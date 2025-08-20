"""
REST API cho CoinJoin Detection System
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import asyncio
import uvicorn

from api.mempool_monitor import MempoolMonitor
from api.neo4j_storage import Neo4jStorage
from utils.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

# Pydantic models
class InvestigationRequest(BaseModel):
    # Unified: accept either txid or address, with optional max_depth (default 10)
    txid: Optional[str] = None
    address: Optional[str] = None
    max_depth: int = 10

class AddressSearchRequest(BaseModel):
    address: str
class LinearInvestigateRequest(BaseModel):
    address: str
    max_depth: int | None = None

class MonitoringStatus(BaseModel):
    is_running: bool
    processed_transactions: int
    detected_coinjoins: int
    last_update: str

class SingleTxTestRequest(BaseModel):
    txid: str

# FastAPI app
app = FastAPI(
    title="CoinJoin Detection API",
    description="API để phát hiện và điều tra CoinJoin transactions",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
config = Config()
mempool_monitor = None
neo4j_storage = Neo4jStorage(config)
monitoring_task = None
monitoring_stats = {
    'is_running': False,
    'processed_transactions': 0,
    'detected_coinjoins': 0,
    'last_update': ''
}

@app.on_event("startup")
async def startup_event():
    """Khởi tạo khi API start: connect Neo4j + preload ML model"""
    try:
        await neo4j_storage.connect()
        # Preload ML model
        try:
            from api.ml_detector import preload_model, is_model_loaded, last_model_error
            loaded = preload_model()
            if loaded:
                logger.info("✅ ML model preloaded")
            else:
                logger.warning(f"⚠️ ML model not available at startup: {last_model_error()}")
        except Exception as me:
            logger.warning(f"⚠️ ML preload error: {me}")
        logger.info("✅ API khởi động thành công")
    except Exception as e:
        logger.error(f"❌ Lỗi khởi động API: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Dọn dẹp khi API shutdown"""
    if mempool_monitor and hasattr(mempool_monitor, 'close'):
        await mempool_monitor.close()
    await neo4j_storage.close()
    logger.info("API đã shutdown")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "CoinJoin Detection API",
        "version": "1.0.0",
        "status": "running"
    }

@app.post("/monitoring/start")
async def start_monitoring(background_tasks: BackgroundTasks):
    """Bắt đầu giám sát mempool"""
    global mempool_monitor, monitoring_task, monitoring_stats
    
    if monitoring_stats['is_running']:
        raise HTTPException(status_code=400, detail="Monitoring đã đang chạy")
    
    try:
        mempool_monitor = MempoolMonitor(config)
        monitoring_task = asyncio.create_task(mempool_monitor.start_monitoring())
        
        monitoring_stats['is_running'] = True
        monitoring_stats['processed_transactions'] = 0
        monitoring_stats['detected_coinjoins'] = 0
        monitoring_stats['last_update'] = asyncio.get_event_loop().time()
        
        logger.info("🚀 Bắt đầu giám sát mempool")
        
        return {
            "message": "Monitoring started successfully",
            "status": "running"
        }
        
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi khởi động monitoring: {str(e)}")

@app.post("/monitoring/stop")
async def stop_monitoring():
    """Dừng giám sát mempool"""
    global monitoring_task, monitoring_stats
    
    if not monitoring_stats['is_running']:
        raise HTTPException(status_code=400, detail="Monitoring chưa chạy")
    
    try:
        if monitoring_task:
            monitoring_task.cancel()
            try:
                await monitoring_task
            except asyncio.CancelledError:
                pass
        
        monitoring_stats['is_running'] = False
        logger.info("⏹️ Dừng giám sát mempool")
        
        return {
            "message": "Monitoring stopped successfully",
            "status": "stopped"
        }
        
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi dừng monitoring: {str(e)}")

@app.get("/monitoring/status")
async def get_monitoring_status() -> MonitoringStatus:
    """Lấy trạng thái monitoring"""
    return MonitoringStatus(**monitoring_stats)

@app.post("/investigate")
async def investigate_transaction(request: InvestigationRequest):
    """Điều tra tuyến tính (gộp):
    - Nếu có txid: phân tích heuristic + ML, nếu CoinJoin thì lưu Neo4j; trả về cây theo dạng {tx, out}
    - Nếu có address: xây cây bắt đầu từ địa chỉ đó
    """
    try:
        from api.coinjoin_investigator import CoinJoinInvestigator
        import aiohttp

        investigator = CoinJoinInvestigator(config)
        max_depth = request.max_depth if isinstance(request.max_depth, int) else 10

        if request.txid:
            # Fetch transaction details
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://blockstream.info/api/tx/{request.txid}") as response:
                    if response.status != 200:
                        raise HTTPException(status_code=404, detail="Transaction không tìm thấy")
                    tx_data = await response.json()

            # Heuristic analysis
            heuristic = await investigator.analyze_transaction_coinjoin(tx_data)
            # ML prediction
            from api.ml_detector import predict_with_model, is_model_loaded
            ml = predict_with_model(tx_data)

            is_cj = bool((heuristic or {}).get('is_coinjoin', False)) or bool((ml or {}).get('is_coinjoin', False))
            if is_cj:
                await investigator.investigate_coinjoin(request.txid, tx_data, heuristic or {})

            tree = await investigator.build_tree_from_txid(request.txid, max_depth=max_depth)
            return {
                "mode": "tx",
                "txid": request.txid,
                "is_coinjoin": is_cj,
                "heuristic": heuristic,
                "ml": ml,
                "tree": tree
            }

        if request.address:
            tree = await investigator.build_tree_from_address(request.address, max_depth=max_depth)
            return {
                "mode": "address",
                "address": request.address,
                "tree": tree
            }

        raise HTTPException(status_code=400, detail="Yêu cầu phải có 'txid' hoặc 'address'")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error investigating transaction: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi điều tra: {str(e)}")

@app.get("/statistics")
async def get_statistics():
    """Lấy thống kê CoinJoin"""
    try:
        stats = await neo4j_storage.get_coinjoin_statistics()
        return {
            "statistics": stats,
            "monitoring_status": monitoring_stats
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi lấy thống kê: {str(e)}")

@app.post("/search/address")
async def search_by_address(request: AddressSearchRequest):
    """Tìm kiếm CoinJoin transactions theo địa chỉ"""
    try:
        results = await neo4j_storage.search_coinjoin_by_address(request.address)
        return {
            "address": request.address,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Error searching by address: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi tìm kiếm: {str(e)}")

# NOTE: Đã gộp /investigate/address vào /investigate

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test Neo4j connection
        await neo4j_storage.connect()
        # Check ML model status
        try:
            from api.ml_detector import is_model_loaded, last_model_error
            ml_status = 'loaded' if is_model_loaded() else f"not_loaded: {last_model_error()}"
        except Exception as me:
            ml_status = f"error: {me}"
        return {
            "status": "healthy",
            "neo4j": "connected",
            "monitoring": monitoring_stats['is_running'],
            "ml_model": ml_status
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.post("/test/single-tx")
async def test_single_tx(request: SingleTxTestRequest):
    """Kiểm tra kết nối DB trước, OK mới chạy logic trên 1 tx và ngừng."""
    try:
        # 1) Check DB connectivity
        can_db = await neo4j_storage.can_connect()
        if not can_db:
            raise HTTPException(status_code=503, detail="Neo4j không kết nối được - dừng test")

        # 2) Fetch tx and analyze once
        from api.coinjoin_investigator import CoinJoinInvestigator
        import aiohttp
        investigator = CoinJoinInvestigator(config)

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://blockstream.info/api/tx/{request.txid}") as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=404, detail="Transaction không tìm thấy")
                tx_data = await resp.json()

        coinjoin_analysis = await investigator.analyze_transaction_coinjoin(tx_data)

        # Không chạy DFS; chỉ trả về kết quả của 1 tx
        return {
            "db": "connected",
            "txid": request.txid,
            "analysis": coinjoin_analysis
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error single tx test: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/coinjoin/graphs")
async def get_all_coinjoin_graphs():
    """Lấy tất cả đồ thị CoinJoin đã lưu trữ"""
    try:
        graphs = await neo4j_storage.get_all_coinjoin_graphs()
        return {"status": "success", "graphs": graphs}
    except Exception as e:
        logger.error(f"Error getting CoinJoin graphs: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/coinjoin/graphs/{investigation_id}")
async def get_coinjoin_graph(investigation_id: str):
    """Lấy đồ thị CoinJoin theo investigation ID"""
    try:
        graph = await neo4j_storage.get_coinjoin_graph_by_id(investigation_id)
        if graph:
            return {"status": "success", "graph": graph}
        else:
            return {"status": "error", "message": "Investigation not found"}
    except Exception as e:
        logger.error(f"Error getting CoinJoin graph: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(
        "api.rest_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
