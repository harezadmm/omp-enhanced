import random
from typing import Tuple
import config

class DiceGame:
    """Game logic untuk dadu besar/kecil"""
    
    def __init__(self):
        self.min_bet = config.MIN_BET
        self.max_bet = config.MAX_BET
        self.house_edge = config.HOUSE_EDGE
    
    def roll_dice(self) -> int:
        """Roll dice 1-6"""
        return random.randint(1, 6)
    
    def calculate_result(self, bet_type: str, bet_amount: int) -> Tuple[int, int, str]:
        """
        Calculate game result
        Returns: (dice_result, win_amount, message)
        """
        dice = self.roll_dice()
        
        # Tentukan besar/kecil
        # 4, 5, 6 = BESAR
        # 1, 2, 3 = KECIL
        is_besar = dice >= 4
        
        win = False
        if bet_type == "besar" and is_besar:
            win = True
        elif bet_type == "kecil" and not is_besar:
            win = True
        
        # Calculate winnings
        if win:
            # Payout 1:1 minus house edge
            payout_multiplier = 1.0 - self.house_edge
            win_amount = int(bet_amount * payout_multiplier)
            
            result_text = f"🎲 Dadu: {dice}\n"
            result_text += f"{'🔴 BESAR' if is_besar else '🔵 KECIL'}\n\n"
            result_text += f"✅ MENANG!\n"
            result_text += f"💰 Kamu dapat: Rp {win_amount:,}"
            
            return (dice, win_amount, result_text)
        else:
            result_text = f"🎲 Dadu: {dice}\n"
            result_text += f"{'🔴 BESAR' if is_besar else '🔵 KECIL'}\n\n"
            result_text += f"❌ KALAH\n"
            result_text += f"💸 Kehilangan: Rp {bet_amount:,}"
            
            return (dice, 0, result_text)
    
    def validate_bet(self, balance: int, bet_amount: int) -> Tuple[bool, str]:
        """Validate bet amount"""
        if bet_amount < self.min_bet:
            return False, f"❌ Bet minimal Rp {self.min_bet:,}"
        
        if bet_amount > self.max_bet:
            return False, f"❌ Bet maksimal Rp {self.max_bet:,}"
        
        if bet_amount > balance:
            return False, f"❌ Saldo tidak cukup!\n💰 Saldo: Rp {balance:,}\n💸 Bet: Rp {bet_amount:,}"
        
        return True, "OK"
    
    def get_dice_emoji(self, number: int) -> str:
        """Get dice emoji"""
        dice_emoji = {
            1: "⚀",
            2: "⚁",
            3: "⚂",
            4: "⚃",
            5: "⚄",
            6: "⚅"
        }
        return dice_emoji.get(number, "🎲")
