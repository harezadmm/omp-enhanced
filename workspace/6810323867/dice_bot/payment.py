import requests
import hashlib
import hmac
import json
from typing import Optional, Dict
import config

class PaymentProcessor:
    """Handle QRIS payment via Tripay"""
    
    def __init__(self):
        self.api_key = config.TRIPAY_API_KEY
        self.private_key = config.TRIPAY_PRIVATE_KEY
        self.merchant_code = config.TRIPAY_MERCHANT_CODE
        self.base_url = "https://tripay.co.id/api"
        
        if config.PAYMENT_PROVIDER == "tripay":
            self.sandbox_url = "https://tripay.co.id/api-sandbox"
            # Gunakan sandbox untuk testing
            self.url = self.sandbox_url
    
    def _generate_signature(self, merchant_ref: str, amount: int) -> str:
        """Generate signature untuk request"""
        string = f"{self.merchant_code}{merchant_ref}{amount}"
        signature = hmac.new(
            self.private_key.encode(),
            string.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def create_qris_payment(self, user_id: int, amount: int) -> Optional[Dict]:
        """Create QRIS payment request"""
        try:
            merchant_ref = f"DEP{user_id}{int(time.time())}"
            signature = self._generate_signature(merchant_ref, amount)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "method": "QRIS",
                "merchant_ref": merchant_ref,
                "amount": amount,
                "customer_name": f"User {user_id}",
                "customer_email": f"user{user_id}@gambling.bot",
                "order_items": [
                    {
                        "name": "Deposit Saldo",
                        "price": amount,
                        "quantity": 1
                    }
                ],
                "callback_url": config.WEBHOOK_URL,
                "return_url": "https://t.me/YOUR_BOT_USERNAME",
                "signature": signature
            }
            
            response = requests.post(
                f"{self.url}/transaction/create",
                headers=headers,
                json=payload,
                timeout=15
            )
            
            result = response.json()
            
            if result.get("success"):
                data = result["data"]
                return {
                    "payment_id": data["reference"],
                    "qris_url": data["qr_url"],
                    "qris_string": data["qr_string"],
                    "amount": amount,
                    "expired_at": data["expired_time"]
                }
            else:
                print(f"Payment creation failed: {result.get('message')}")
                return None
                
        except Exception as e:
            print(f"Payment error: {e}")
            return None
    
    def check_payment_status(self, payment_id: str) -> Optional[str]:
        """Check payment status"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            response = requests.get(
                f"{self.url}/transaction/detail",
                headers=headers,
                params={"reference": payment_id},
                timeout=10
            )
            
            result = response.json()
            
            if result.get("success"):
                status = result["data"]["status"]
                # UNPAID, PAID, FAILED, EXPIRED, REFUND
                return status
            
            return None
            
        except Exception as e:
            print(f"Status check error: {e}")
            return None
    
    def verify_callback(self, callback_data: Dict) -> bool:
        """Verify callback signature from Tripay"""
        try:
            received_signature = callback_data.get("signature")
            
            # Generate signature from callback data
            string = f"{self.merchant_code}{callback_data['merchant_ref']}{callback_data['amount']}"
            expected_signature = hmac.new(
                self.private_key.encode(),
                string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return received_signature == expected_signature
            
        except Exception as e:
            print(f"Signature verification error: {e}")
            return False

import time
