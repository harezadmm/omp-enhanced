#!/usr/bin/env python3
"""
WhatsApp Nokos (Phone Number) Auto Farmer
Auto-registers WhatsApp accounts using free temporary phone numbers
"""

import requests
import time
import json
import random
import string
from datetime import datetime
from typing import Optional, Dict, List

class SMSProvider:
    """Base class for SMS providers"""
    def get_number(self) -> Optional[Dict[str, str]]:
        raise NotImplementedError
    
    def get_code(self, number_id: str) -> Optional[str]:
        raise NotImplementedError

class SMSActivateRU(SMSProvider):
    """sms-activate.ru provider (requires API key, but has free trial)"""
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.base_url = "https://api.sms-activate.org/stubs/handler_api.php"
    
    def get_number(self) -> Optional[Dict[str, str]]:
        try:
            params = {
                "api_key": self.api_key,
                "action": "getNumber",
                "service": "wa",  # WhatsApp
                "country": "6"  # Indonesia (cheaper, change as needed)
            }
            resp = requests.get(self.base_url, params=params, timeout=10)
            if "ACCESS_NUMBER" in resp.text:
                parts = resp.text.split(":")
                return {
                    "id": parts[1],
                    "number": parts[2],
                    "provider": "sms-activate"
                }
        except Exception as e:
            print(f"[SMS-Activate] Error: {e}")
        return None
    
    def get_code(self, number_id: str) -> Optional[str]:
        try:
            params = {
                "api_key": self.api_key,
                "action": "getStatus",
                "id": number_id
            }
            resp = requests.get(self.base_url, params=params, timeout=10)
            if "STATUS_OK" in resp.text:
                code = resp.text.split(":")[1]
                return code
        except Exception as e:
            print(f"[SMS-Activate] Code error: {e}")
        return None

class ReceiveSMSFree(SMSProvider):
    """receive-smss.com - completely free but limited"""
    def __init__(self):
        self.base_url = "https://receive-smss.com"
        self.numbers_cache = []
    
    def get_number(self) -> Optional[Dict[str, str]]:
        try:
            # Scrape available numbers
            resp = requests.get(f"{self.base_url}/", timeout=10)
            # Parse numbers from HTML (simplified, would need proper parsing)
            # This is a placeholder - real implementation needs HTML parsing
            numbers = [
                "+12012673961",
                "+12013804817",
                "+12013804862"
            ]
            if numbers:
                num = random.choice(numbers)
                return {
                    "id": num,
                    "number": num.replace("+", ""),
                    "provider": "receive-smss"
                }
        except Exception as e:
            print(f"[ReceiveSMSFree] Error: {e}")
        return None
    
    def get_code(self, number_id: str) -> Optional[str]:
        try:
            # Check messages for this number
            # Placeholder - needs HTML scraping implementation
            time.sleep(2)
            return None
        except Exception as e:
            print(f"[ReceiveSMSFree] Code error: {e}")
        return None

class FreeOnlinePhone(SMSProvider):
    """freeonlinephone.org - free public numbers"""
    def __init__(self):
        self.numbers = [
            "12016327663",
            "12018163676",
            "12018643722"
        ]
    
    def get_number(self) -> Optional[Dict[str, str]]:
        num = random.choice(self.numbers)
        return {
            "id": num,
            "number": num,
            "provider": "freeonlinephone"
        }
    
    def get_code(self, number_id: str) -> Optional[str]:
        # Placeholder - needs proper implementation
        return None

class WhatsAppRegistration:
    """Handle WhatsApp registration process"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "WhatsApp/2.23.20.0 Android/11",
            "Content-Type": "application/x-www-form-urlencoded"
        })
        self.client_id = self._generate_client_id()
    
    def _generate_client_id(self) -> str:
        """Generate random device ID"""
        return ''.join(random.choices(string.hexdigits.lower(), k=16))
    
    def request_code(self, phone_number: str, country_code: str = "62") -> bool:
        """Request verification code via SMS"""
        try:
            # WhatsApp registration endpoint (simplified)
            url = "https://v.whatsapp.net/v2/code"
            
            data = {
                "cc": country_code,
                "phone": phone_number,
                "method": "sms",
                "mcc": "510",  # Indonesia MCC
                "mnc": "010",  # Indosat MNC
                "sim_mcc": "000",
                "sim_mnc": "000",
                "client_metrics": "",
                "reason": "",
                "id": self.client_id
            }
            
            resp = self.session.post(url, data=data, timeout=15)
            result = resp.json()
            
            if result.get("status") == "sent":
                print(f"✅ Code requested for +{country_code}{phone_number}")
                return True
            else:
                print(f"❌ Failed to request code: {result.get('reason', 'unknown')}")
                return False
                
        except Exception as e:
            print(f"❌ Request code error: {e}")
            return False
    
    def verify_code(self, phone_number: str, code: str, country_code: str = "62") -> bool:
        """Verify the received code"""
        try:
            url = "https://v.whatsapp.net/v2/register"
            
            data = {
                "cc": country_code,
                "phone": phone_number,
                "code": code.replace("-", ""),
                "id": self.client_id
            }
            
            resp = self.session.post(url, data=data, timeout=15)
            result = resp.json()
            
            if result.get("status") == "ok":
                print(f"✅ Account registered: +{country_code}{phone_number}")
                return True
            else:
                print(f"❌ Verification failed: {result.get('reason', 'unknown')}")
                return False
                
        except Exception as e:
            print(f"❌ Verify error: {e}")
            return False

class WhatsAppNokosAutoFarmer:
    """Main auto-farmer orchestrator"""
    
    def __init__(self):
        self.providers: List[SMSProvider] = [
            ReceiveSMSFree(),
            FreeOnlinePhone(),
            # SMSActivateRU(api_key="YOUR_API_KEY_HERE")  # Uncomment if you have API key
        ]
        self.wa = WhatsAppRegistration()
        self.accounts = []
        self.stats = {
            "attempts": 0,
            "success": 0,
            "failed": 0,
            "start_time": datetime.now()
        }
    
    def save_account(self, phone: str, data: Dict):
        """Save successful account to file"""
        account_data = {
            "phone": phone,
            "registered_at": datetime.now().isoformat(),
            "data": data
        }
        self.accounts.append(account_data)
        
        with open("/root/workspace/6810323867/whatsapp_accounts.json", "w") as f:
            json.dump(self.accounts, f, indent=2)
        
        print(f"💾 Account saved: {phone}")
    
    def print_stats(self):
        """Print current statistics"""
        elapsed = (datetime.now() - self.stats["start_time"]).total_seconds()
        rate = self.stats["success"] / (elapsed / 60) if elapsed > 0 else 0
        
        print("\n" + "="*50)
        print("📊 STATISTICS")
        print("="*50)
        print(f"Attempts:  {self.stats['attempts']}")
        print(f"Success:   {self.stats['success']} ✅")
        print(f"Failed:    {self.stats['failed']} ❌")
        print(f"Time:      {int(elapsed)}s")
        print(f"Rate:      {rate:.2f} accounts/min")
        print("="*50 + "\n")
    
    def farm_single_account(self) -> bool:
        """Attempt to create one WhatsApp account"""
        self.stats["attempts"] += 1
        
        print(f"\n🔄 Attempt #{self.stats['attempts']}")
        
        # Try each provider until we get a number
        number_data = None
        provider = None
        
        for p in self.providers:
            print(f"🔍 Trying provider: {p.__class__.__name__}")
            number_data = p.get_number()
            if number_data:
                provider = p
                break
            time.sleep(1)
        
        if not number_data:
            print("❌ No providers available")
            self.stats["failed"] += 1
            return False
        
        phone = number_data["number"]
        number_id = number_data["id"]
        
        print(f"📱 Got number: +{phone} from {number_data['provider']}")
        
        # Request verification code
        if not self.wa.request_code(phone):
            self.stats["failed"] += 1
            return False
        
        # Wait for SMS and retrieve code
        print("⏳ Waiting for verification code...")
        code = None
        
        for attempt in range(12):  # Try for 2 minutes (12 * 10s)
            time.sleep(10)
            code = provider.get_code(number_id)
            if code:
                print(f"📩 Received code: {code}")
                break
            print(f"   Checking... ({attempt + 1}/12)")
        
        if not code:
            print("❌ Timeout waiting for code")
            self.stats["failed"] += 1
            return False
        
        # Verify code and register
        if self.wa.verify_code(phone, code):
            self.save_account(phone, number_data)
            self.stats["success"] += 1
            return True
        else:
            self.stats["failed"] += 1
            return False
    
    def run(self, target_accounts: int = 10, delay_between: int = 30):
        """Main farming loop"""
        print("="*50)
        print("🤖 WhatsApp Nokos Auto Farmer")
        print("="*50)
        print(f"Target: {target_accounts} accounts")
        print(f"Delay:  {delay_between}s between attempts")
        print("="*50 + "\n")
        
        while self.stats["success"] < target_accounts:
            try:
                self.farm_single_account()
                self.print_stats()
                
                if self.stats["success"] < target_accounts:
                    print(f"⏸️  Waiting {delay_between}s before next attempt...")
                    time.sleep(delay_between)
                    
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                time.sleep(5)
        
        print("\n" + "="*50)
        print("🎉 FARMING COMPLETE!")
        print("="*50)
        self.print_stats()
        print(f"📁 Accounts saved to: whatsapp_accounts.json")

if __name__ == "__main__":
    farmer = WhatsAppNokosAutoFarmer()
    
    # Configuration
    TARGET_ACCOUNTS = 5  # Change this to desired number
    DELAY_SECONDS = 30   # Delay between attempts to avoid rate limiting
    
    farmer.run(target_accounts=TARGET_ACCOUNTS, delay_between=DELAY_SECONDS)
