from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np
from app.models import Configuration, SimulationResult
from app.services.simulation_service import SimulationService
from app.constants import DEFAULT_TARGET_MULTIPLIER, DEFAULT_TARGET_FALLBACK
import logging

logger = logging.getLogger(__name__)


class ResultsService:
    """Service for managing and retrieving results"""

    def __init__(self, db: Session):
        self.db = db

    def save_results(self, result_id: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save simulation or analysis results
        
        Args:
            result_id: Unique identifier for the results
            results: Dictionary containing results data
            
        Returns:
            Dictionary with save results
        """
        # TODO: Implement results persistence
        return {
            "status": "success",
            "result_id": result_id,
            "message": "Results saved successfully"
        }

    def get_results(self, result_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve results by ID
        
        Args:
            result_id: Unique identifier for the results
            
        Returns:
            Results dictionary or None if not found
        """
        # TODO: Implement results retrieval
        return None

    def list_results(self, filters: Optional[Dict[str, Any]] = None, 
                    offset: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List all results with optional filters and pagination
        
        Args:
            filters: Optional dictionary of filter criteria
            offset: Number of results to skip (for pagination)
            limit: Maximum number of results to return
            
        Returns:
            List of result dictionaries
        """
        query = self.db.query(SimulationResult)
        
        if filters:
            for key, value in filters.items():
                if hasattr(SimulationResult, key):
                    query = query.filter(getattr(SimulationResult, key) == value)
        
        # Apply pagination
        results = query.offset(offset).limit(limit).all()
        
        return [
            {
                "id": r.id,
                "config_id": r.config_id,
                "n_total": r.n_total,
                "run_index": r.run_index,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            } for r in results
        ]
    
    def count_results(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count total number of results matching filters
        
        Args:
            filters: Optional dictionary of filter criteria
            
        Returns:
            Total count of matching results
        """
        query = self.db.query(SimulationResult)
        
        if filters:
            for key, value in filters.items():
                if hasattr(SimulationResult, key):
                    query = query.filter(getattr(SimulationResult, key) == value)
        
        return query.count()

    def delete_results(self, result_id: str) -> Dict[str, Any]:
        """
        Delete results by ID
        
        Args:
            result_id: Unique identifier for the results
            
        Returns:
            Dictionary with deletion results
        """
        # TODO: Implement results deletion
        return {
            "status": "success",
            "result_id": result_id,
            "message": "Results deleted successfully"
        }

    def export_results(self, result_id: str, format: str = "json") -> Dict[str, Any]:
        """
        Export results in specified format
        
        Args:
            result_id: Unique identifier for the results
            format: Export format (json, csv, etc.)
            
        Returns:
            Dictionary with export data
        """
        # TODO: Implement results export
        return {
            "status": "success",
            "result_id": result_id,
            "format": format,
            "data": {}
        }

    def summarize(self, config_id: str, target: Optional[float] = None, 
                  n_runs: Optional[int] = None, risk_profile: Optional[str] = None) -> Dict[str, Any]:
        """
        Summarize simulation results for a configuration
        
        Steps:
        1. Retrieve simulation results or call simulation_service
        2. Compute mean, p5, p50, p95
        3. Compute P_hit for target stored in config or default
        4. Return JSON
        
        Args:
            config_id: Configuration ID to summarize
            target: Optional target value for P_hit calculation (overrides config default)
            n_runs: Optional number of runs if simulation needs to be run
            risk_profile: Optional risk profile ID if simulation needs to be run
            
        Returns:
            Dictionary with summary statistics
        """
        try:
            # Step 1: Retrieve simulation results or call simulation_service
            existing_results = self.db.query(SimulationResult).filter(
                SimulationResult.config_id == config_id
            ).all()
            
            n_totals = None
            
            if not existing_results and n_runs is not None:
                # No results exist, run simulation
                sim_service = SimulationService(self.db)
                sim_result = sim_service.simulate(config_id, n_runs, risk_profile)
                
                if sim_result.get("status") != "success":
                    return {
                        "status": "error",
                        "message": f"Failed to run simulation: {sim_result.get('message')}"
                    }
                
                n_totals = np.array(sim_result.get("n_totals", []))
            elif existing_results:
                # Use existing results
                n_totals = np.array([result.n_total for result in existing_results if result.n_total is not None])
            else:
                return {
                    "status": "error",
                    "message": f"No simulation results found for {config_id} and n_runs not provided"
                }
            
            if len(n_totals) == 0:
                return {
                    "status": "error",
                    "message": f"No valid simulation results for {config_id}"
                }
            
            # Step 2: Compute statistics
            mean = float(np.mean(n_totals))
            p5 = float(np.percentile(n_totals, 5))
            p50 = float(np.percentile(n_totals, 50))
            p95 = float(np.percentile(n_totals, 95))
            
            # Step 3: Compute P_hit for target
            # Get target from config or use provided/default
            if target is None:
                config = self.db.query(Configuration).filter(
                    Configuration.config_id == config_id
                ).first()
                
                if config:
                    # Check if target is stored in config (might be in a JSON field or separate field)
                    # For now, use a default target based on application rate
                    # You can extend this to store target in config if needed
                    if config.application_rate_t_ha is not None:
                        # Default target: multiplier x application rate
                        target = config.application_rate_t_ha * DEFAULT_TARGET_MULTIPLIER
                    else:
                        target = DEFAULT_TARGET_FALLBACK
                else:
                    target = DEFAULT_TARGET_FALLBACK
            
            # P_hit = probability that n_total >= target
            p_hit = float(np.mean(n_totals >= target))
            
            # Step 4: Return JSON
            return {
                "status": "success",
                "config_id": config_id,
                "statistics": {
                    "mean": mean,
                    "p5": p5,
                    "p50": p50,
                    "p95": p95,
                    "std": float(np.std(n_totals)),
                    "min": float(np.min(n_totals)),
                    "max": float(np.max(n_totals)),
                    "count": len(n_totals)
                },
                "target": float(target),
                "p_hit": p_hit,
                "n_runs": len(n_totals)
            }
            
        except Exception as e:
            logger.error(f"Error summarizing results for {config_id}: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": "An error occurred while summarizing results"
            }

