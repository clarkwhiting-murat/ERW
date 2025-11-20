from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
import numpy as np
import pandas as pd
from scipy.special import expit  # logistic function
from app.models import Configuration, StatePosterior, RiskProfile, SimulationResult
from app.constants import SIMULATION_MONTHS
import logging

logger = logging.getLogger(__name__)


class SimulationService:
    """Service for running simulations"""

    def __init__(self, db: Session):
        self.db = db

    def run_simulation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a simulation with given parameters
        
        Args:
            parameters: Dictionary containing simulation parameters
            
        Returns:
            Dictionary with simulation results
        """
        # TODO: Implement simulation logic
        return {
            "status": "success",
            "simulation_id": "sim_123",
            "results": {},
            "message": "Simulation completed successfully"
        }

    def get_simulation_status(self, simulation_id: str) -> Dict[str, Any]:
        """
        Get the status of a running simulation
        
        Args:
            simulation_id: Unique identifier for the simulation
            
        Returns:
            Dictionary with simulation status
        """
        # TODO: Implement status checking
        return {
            "simulation_id": simulation_id,
            "status": "completed",
            "progress": 100
        }

    def cancel_simulation(self, simulation_id: str) -> Dict[str, Any]:
        """
        Cancel a running simulation
        
        Args:
            simulation_id: Unique identifier for the simulation
            
        Returns:
            Dictionary with cancellation results
        """
        # TODO: Implement cancellation logic
        return {
            "status": "success",
            "simulation_id": simulation_id,
            "message": "Simulation cancelled successfully"
        }

    def validate_parameters(self, parameters: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate simulation parameters
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # TODO: Implement parameter validation
        return True, None

    def simulate(self, config_id: str, n_runs: int, risk_profile: Optional[str] = None) -> Dict[str, Any]:
        """
        Run simulation for a configuration
        
        Steps:
        1. Load config, posterior, risk data
        2. For each run i:
           - Sample initial eta_r0, eta_phi0
           - Simulate 120 months
           - Apply risk multipliers
           - Sum N_total
        3. Return array or store SimulationResult rows
        
        Args:
            config_id: Configuration ID to simulate
            n_runs: Number of simulation runs
            risk_profile: Optional risk profile ID
            
        Returns:
            Dictionary with simulation results
        """
        try:
            # Step 1: Load config, posterior, risk data
            config = self.db.query(Configuration).filter(
                Configuration.config_id == config_id
            ).first()
            
            if not config:
                return {
                    "status": "error",
                    "message": f"Configuration {config_id} not found"
                }
            
            # Get the most recent posterior
            posterior = self.db.query(StatePosterior).filter(
                StatePosterior.config_id == config_id
            ).order_by(StatePosterior.created_at.desc()).first()
            
            if not posterior:
                return {
                    "status": "error",
                    "message": f"No posterior found for configuration {config_id}. Run update_state first."
                }
            
            # Load risk profile if provided
            risk_multipliers = None
            if risk_profile:
                risk = self.db.query(RiskProfile).filter(
                    RiskProfile.risk_id == risk_profile
                ).first()
                
                if not risk:
                    return {
                        "status": "error",
                        "message": f"Risk profile {risk_profile} not found"
                    }
                
                if risk.parameters:
                    # Extract multipliers from risk parameters
                    # Assuming parameters is a dict with multipliers per month or a single multiplier
                    risk_multipliers = risk.parameters.get("multipliers", None)
                    if risk_multipliers is None:
                        # If no multipliers key, assume the whole parameters dict contains multipliers
                        risk_multipliers = risk.parameters
            
            # Extract configuration parameters
            A = config.application_rate_t_ha
            K = config.chemistry_factor_K
            
            if A is None or K is None:
                return {
                    "status": "error",
                    "message": f"Configuration {config_id} missing required parameters (application_rate_t_ha or chemistry_factor_K)"
                }
            
            # Extract posterior parameters
            eta_r0_mean = posterior.eta_r0_mean
            eta_r0_var = posterior.eta_r0_var
            eta_phi0_mean = posterior.eta_phi0_mean
            eta_phi0_var = posterior.eta_phi0_var
            alpha_r = posterior.alpha_r
            alpha_phi = posterior.alpha_phi
            sigma_r = posterior.sigma_r
            sigma_phi = posterior.sigma_phi
            
            if any(x is None for x in [eta_r0_mean, eta_r0_var, eta_phi0_mean, eta_phi0_var, 
                                       alpha_r, alpha_phi, sigma_r, sigma_phi]):
                return {
                    "status": "error",
                    "message": f"Posterior for {config_id} has missing parameters"
                }
            
            # Step 2: Run simulations
            n_months = SIMULATION_MONTHS
            n_totals = []
            simulation_results = []
            
            for run_i in range(n_runs):
                # Sample initial eta_r0, eta_phi0 from posterior
                eta_r = np.random.normal(eta_r0_mean, np.sqrt(eta_r0_var))
                eta_phi = np.random.normal(eta_phi0_mean, np.sqrt(eta_phi0_var))
                
                # Initialize arrays for simulation
                N = np.zeros(n_months)
                
                # Simulate 120 months
                for t in range(n_months):
                    # State transition
                    # eta_r[t] = eta_r[t-1] + alpha_r + Normal(0, sigma_r)
                    eta_r = eta_r + alpha_r + np.random.normal(0, sigma_r)
                    # eta_phi[t] = eta_phi[t-1] + alpha_phi + Normal(0, sigma_phi)
                    eta_phi = eta_phi + alpha_phi + np.random.normal(0, sigma_phi)
                    
                    # Transform to r and phi
                    r_t = np.exp(eta_r)
                    phi_t = expit(eta_phi)  # logistic function: 1 / (1 + exp(-eta_phi))
                    
                    # Calculate N[t] = A * K * r[t] * phi[t]
                    N_t = A * K * r_t * phi_t
                    
                    # Apply risk multipliers if available
                    if risk_multipliers is not None:
                        if isinstance(risk_multipliers, (list, np.ndarray)):
                            # If multipliers is an array, use the t-th element
                            if t < len(risk_multipliers):
                                multiplier = risk_multipliers[t]
                            else:
                                # If array is shorter, use the last value
                                multiplier = risk_multipliers[-1] if len(risk_multipliers) > 0 else 1.0
                        elif isinstance(risk_multipliers, dict):
                            # If multipliers is a dict, try to get month-specific or use default
                            multiplier = risk_multipliers.get(str(t), risk_multipliers.get("default", 1.0))
                        else:
                            # Single multiplier value
                            multiplier = float(risk_multipliers)
                        
                        N_t = N_t * multiplier
                    
                    N[t] = N_t
                
                # Sum N_total
                n_total = np.sum(N)
                n_totals.append(n_total)
                
                # Store SimulationResult
                sim_result = SimulationResult(
                    config_id=config_id,
                    n_total=float(n_total),
                    run_index=run_i
                )
                simulation_results.append(sim_result)
            
            # Bulk insert simulation results
            self.db.add_all(simulation_results)
            self.db.commit()
            
            return {
                "status": "success",
                "config_id": config_id,
                "n_runs": n_runs,
                "n_totals": [float(x) for x in n_totals],
                "summary": {
                    "mean": float(np.mean(n_totals)),
                    "std": float(np.std(n_totals)),
                    "min": float(np.min(n_totals)),
                    "max": float(np.max(n_totals)),
                    "p5": float(np.percentile(n_totals, 5)),
                    "p50": float(np.percentile(n_totals, 50)),
                    "p95": float(np.percentile(n_totals, 95))
                },
                "risk_profile": risk_profile if risk_profile else None
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error running simulation for {config_id}: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": "An error occurred while running simulation"
            }

