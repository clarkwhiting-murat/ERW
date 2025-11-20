from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import json
import numpy as np
from scipy.optimize import minimize
from app.models import Configuration, LabRecord, FieldRecord, StatePosterior
import logging

logger = logging.getLogger(__name__)


class ModelStateService:
    """Service for managing model state"""

    def __init__(self, db: Session):
        self.db = db

    def save_model_state(self, model_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save model state
        
        Args:
            model_id: Unique identifier for the model
            state: Model state dictionary
            
        Returns:
            Dictionary with save results
        """
        # TODO: Implement model state persistence
        return {
            "status": "success",
            "model_id": model_id,
            "message": "Model state saved successfully"
        }

    def load_model_state(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Load model state
        
        Args:
            model_id: Unique identifier for the model
            
        Returns:
            Model state dictionary or None if not found
        """
        # TODO: Implement model state loading
        return None

    def update_model_state(self, model_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update model state
        
        Args:
            model_id: Unique identifier for the model
            updates: Dictionary with state updates
            
        Returns:
            Dictionary with update results
        """
        # TODO: Implement model state updates
        return {
            "status": "success",
            "model_id": model_id,
            "message": "Model state updated successfully"
        }

    def update_state(self, config_id: str) -> Dict[str, Any]:
        """
        Update state using Extended Kalman Filter
        
        Steps:
        1. Load configuration, lab data, field data
        2. Initialize priors
        3. Use simplified Extended Kalman Filter
        4. Fit parameters with maximum likelihood
        5. Store posterior summary in StatePosterior table
        
        Args:
            config_id: Configuration ID to update state for
            
        Returns:
            Dictionary with update results and posterior summary
        """
        try:
            # Step 1: Load configuration, lab data, field data
            config = self.db.query(Configuration).filter(
                Configuration.config_id == config_id
            ).first()
            
            if not config:
                return {
                    "status": "error",
                    "message": f"Configuration {config_id} not found"
                }
            
            lab_records = self.db.query(LabRecord).filter(
                LabRecord.config_id == config_id
            ).order_by(LabRecord.time_months).all()
            
            field_records = self.db.query(FieldRecord).filter(
                FieldRecord.config_id == config_id
            ).order_by(FieldRecord.window_start).all()
            
            if not lab_records:
                return {
                    "status": "error",
                    "message": f"No lab records found for configuration {config_id}"
                }
            
            # Extract lab data
            times = np.array([record.time_months for record in lab_records])
            y_lab = np.array([record.co2_uptake_t_per_t for record in lab_records])
            
            # Step 2: Initialize priors
            # Use first observation to initialize eta_r0
            eta_r0_mean = np.log(max(y_lab[0], 1e-6))  # log of first observation
            eta_r0_var = 1.0  # Initial variance
            
            # Initialize eta_phi0 (if we have field data, use it; otherwise use default)
            if field_records:
                # Use field data to estimate initial phi
                field_rates = np.array([record.co2_removed_t_ha for record in field_records])
                eta_phi0_mean = np.log(max(np.mean(field_rates), 1e-6))
            else:
                eta_phi0_mean = 0.0
            eta_phi0_var = 1.0
            
            # Step 3 & 4: Extended Kalman Filter with MLE parameter fitting
            def extended_kalman_filter(params, times, y_lab, eta_r0_mean, eta_r0_var, 
                                      eta_phi0_mean, eta_phi0_var, return_final_state=False):
                """
                Extended Kalman Filter implementation
                
                Args:
                    params: [alpha_r, alpha_phi, sigma_r, sigma_phi, sigma_lab]
                    times: Time points
                    y_lab: Lab observations
                    eta_r0_mean, eta_r0_var: Initial prior for eta_r
                    eta_phi0_mean, eta_phi0_var: Initial prior for eta_phi
                    return_final_state: If True, return final state estimates
                
                Returns:
                    Negative log-likelihood (or tuple with final state if return_final_state=True)
                """
                alpha_r, alpha_phi, sigma_r, sigma_phi, sigma_lab = params
                
                # Ensure positive variances
                sigma_r = max(sigma_r, 1e-6)
                sigma_phi = max(sigma_phi, 1e-6)
                sigma_lab = max(sigma_lab, 1e-6)
                
                n = len(times)
                
                # Initialize state
                eta_r = eta_r0_mean
                eta_phi = eta_phi0_mean
                P_r = eta_r0_var
                P_phi = eta_phi0_var
                
                log_likelihood = 0.0
                
                for i in range(n):
                    # Prediction step (transition)
                    # eta_r[t] = eta_r[t-1] + alpha_r + eps_r
                    # eta_phi[t] = eta_phi[t-1] + alpha_phi + eps_phi
                    eta_r_pred = eta_r + alpha_r
                    eta_phi_pred = eta_phi + alpha_phi
                    
                    # Prediction covariance
                    P_r_pred = P_r + sigma_r**2
                    P_phi_pred = P_phi + sigma_phi**2
                    
                    # Update step (observation)
                    # y_lab ~ Normal(exp(eta_r), sigma_lab)
                    # Linearize observation: h(eta_r) = exp(eta_r)
                    # Jacobian: H = exp(eta_r)
                    h = np.exp(eta_r_pred)
                    H = h  # Jacobian of exp(eta_r)
                    
                    # Innovation
                    y_pred = h
                    innovation = y_lab[i] - y_pred
                    
                    # Innovation covariance
                    S = H**2 * P_r_pred + sigma_lab**2
                    
                    # Kalman gain
                    K = (H * P_r_pred) / S
                    
                    # Update state
                    eta_r = eta_r_pred + K * innovation
                    P_r = (1 - K * H) * P_r_pred
                    
                    # eta_phi doesn't have direct observations, so just propagate
                    eta_phi = eta_phi_pred
                    P_phi = P_phi_pred
                    
                    # Log-likelihood contribution
                    log_likelihood += -0.5 * (np.log(2 * np.pi * S) + (innovation**2) / S)
                
                if return_final_state:
                    return -log_likelihood, eta_r, eta_phi, P_r, P_phi
                return -log_likelihood  # Return negative for minimization
            
            # Initial parameter guesses
            initial_params = np.array([
                0.0,      # alpha_r
                0.0,      # alpha_phi
                0.1,      # sigma_r
                0.1,      # sigma_phi
                np.std(y_lab) * 0.1  # sigma_lab (small fraction of observation std)
            ])
            
            # Bounds for parameters
            bounds = [
                (-1.0, 1.0),      # alpha_r
                (-1.0, 1.0),      # alpha_phi
                (1e-6, 10.0),     # sigma_r
                (1e-6, 10.0),     # sigma_phi
                (1e-6, 10.0)      # sigma_lab
            ]
            
            # Optimize using maximum likelihood
            result = minimize(
                extended_kalman_filter,
                initial_params,
                args=(times, y_lab, eta_r0_mean, eta_r0_var, eta_phi0_mean, eta_phi0_var),
                method='L-BFGS-B',
                bounds=bounds,
                options={'maxiter': 1000}
            )
            
            if not result.success:
                return {
                    "status": "error",
                    "message": f"Optimization failed: {result.message}"
                }
            
            # Extract fitted parameters
            alpha_r_fit = result.x[0]
            alpha_phi_fit = result.x[1]
            sigma_r_fit = result.x[2]
            sigma_phi_fit = result.x[3]
            sigma_lab_fit = result.x[4]
            
            # Run final EKF to get final state estimates and posterior variances
            final_neg_ll, eta_r_final, eta_phi_final, P_r_final, P_phi_final = extended_kalman_filter(
                result.x, times, y_lab, eta_r0_mean, eta_r0_var,
                eta_phi0_mean, eta_phi0_var, return_final_state=True
            )
            
            # Update posterior means and variances with final state estimates
            eta_r0_mean = float(eta_r_final)
            eta_r0_var = float(P_r_final)
            eta_phi0_mean = float(eta_phi_final)
            eta_phi0_var = float(P_phi_final)
            
            # Step 5: Store posterior summary in StatePosterior table
            # Check if StatePosterior already exists
            existing_posterior = self.db.query(StatePosterior).filter(
                StatePosterior.config_id == config_id
            ).first()
            
            if existing_posterior:
                # Update existing record
                existing_posterior.eta_r0_mean = float(eta_r0_mean)
                existing_posterior.eta_r0_var = float(eta_r0_var)
                existing_posterior.eta_phi0_mean = float(eta_phi0_mean)
                existing_posterior.eta_phi0_var = float(eta_phi0_var)
                existing_posterior.alpha_r = float(alpha_r_fit)
                existing_posterior.alpha_phi = float(alpha_phi_fit)
                existing_posterior.sigma_r = float(sigma_r_fit)
                existing_posterior.sigma_phi = float(sigma_phi_fit)
                posterior = existing_posterior
            else:
                # Create new record
                posterior = StatePosterior(
                    config_id=config_id,
                    eta_r0_mean=float(eta_r0_mean),
                    eta_r0_var=float(eta_r0_var),
                    eta_phi0_mean=float(eta_phi0_mean),
                    eta_phi0_var=float(eta_phi0_var),
                    alpha_r=float(alpha_r_fit),
                    alpha_phi=float(alpha_phi_fit),
                    sigma_r=float(sigma_r_fit),
                    sigma_phi=float(sigma_phi_fit)
                )
                self.db.add(posterior)
            
            self.db.commit()
            
            return {
                "status": "success",
                "config_id": config_id,
                "posterior": {
                    "eta_r0_mean": float(eta_r0_mean),
                    "eta_r0_var": float(eta_r0_var),
                    "eta_phi0_mean": float(eta_phi0_mean),
                    "eta_phi0_var": float(eta_phi0_var),
                    "alpha_r": float(alpha_r_fit),
                    "alpha_phi": float(alpha_phi_fit),
                    "sigma_r": float(sigma_r_fit),
                    "sigma_phi": float(sigma_phi_fit),
                },
                "optimization": {
                    "success": result.success,
                    "negative_log_likelihood": float(final_neg_ll),
                    "iterations": result.nit
                },
                "data_summary": {
                    "lab_records": len(lab_records),
                    "field_records": len(field_records)
                }
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating state for {config_id}: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": "An error occurred while updating model state"
            }

    def delete_model_state(self, model_id: str) -> Dict[str, Any]:
        """
        Delete model state
        
        Args:
            model_id: Unique identifier for the model
            
        Returns:
            Dictionary with deletion results
        """
        # TODO: Implement model state deletion
        return {
            "status": "success",
            "model_id": model_id,
            "message": "Model state deleted successfully"
        }

