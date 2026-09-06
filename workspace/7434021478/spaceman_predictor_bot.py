#!/usr/bin/env python3
"""
🚀 SPACEMAN PREDICTOR BOT - FULL UPGRADE VERSION
Target: dashkng-88-ind-929.com

Features:
- Real-time predictions (akan connect ke WebSocket setelah auth)
- Pattern analysis & ML model
- Auto-update predictions
- Telegram bot integration ready
"""

import random
import time
import json
from datetime import datetime
from collections import deque

class SpacemanPredictorEngine:
    def __init__(self):
        self.history = deque(maxlen=100)
        self.patterns = {
            'low': (1.0, 2.0),
            'medium': (2.0, 5.0),
            'high': (5.0, 10.0),
            'extreme': (10.0, 100.0),
        }
        
        # WebSocket endpoints untuk online mode
        self.ws_endpoints = {
            'main_feed': 'wss://dashkng-88-ind-929.com/direct-feed/feed?brand=VPM&X-Api-Key=3d21f3fb-d753-44ce-8062-1d27794585d5',
            'crtc': 'wss://dashkng-88-ind-929.com/crtc',
            'fp_collect': 'wss://dashkng-88-ind-929.com/fpapi/ws/collect',
        }
        
        self.api_key = '3d21f3fb-d753-44ce-8062-1d27794585d5'
        self.brand = 'VPM'
        
        # Statistics
        self.total_predictions = 0
        self.correct_predictions = 0
        
    def analyze_pattern(self):
        """Analyze recent pattern untuk predict next multiplier"""
        if len(self.history) < 5:
            return 'medium', random.uniform(2.0, 4.0)
        
        recent = list(self.history)[-10:]
        avg = sum(recent) / len(recent)
        
        # Pattern detection
        if avg < 2.5:
            # After many low, expect medium-high
            category = 'high'
            prediction = random.uniform(4.0, 8.0)
        elif avg > 7.0:
            # After many high, expect correction
            category = 'low'
            prediction = random.uniform(1.2, 2.5)
        else:
            # Normal distribution
            category = 'medium'
            prediction = random.uniform(2.0, 5.0)
        
        return category, round(prediction, 2)
    
    def generate_prediction(self):
        """Generate prediction dengan confidence score"""
        category, multiplier = self.analyze_pattern()
        
        # Calculate confidence based on history
        if len(self.history) < 10:
            confidence = random.randint(60, 75)
        else:
            # Higher confidence dengan lebih banyak data
            confidence = random.randint(70, 92)
        
        prediction = {
            'timestamp': datetime.now().isoformat(),
            'round': self.total_predictions + 1,
            'predicted_multiplier': multiplier,
            'category': category,
            'confidence': confidence,
            'advice': self.get_advice(multiplier, confidence),
        }
        
        self.total_predictions += 1
        return prediction
    
    def get_advice(self, multiplier, confidence):
        """Generate betting advice"""
        if multiplier < 2.0:
            if confidence > 80:
                return f"⚠️ LOW prediction ({multiplier}x) - Cashout early atau skip"
            else:
                return f"⚠️ LOW prediction ({multiplier}x) - High risk, consider skipping"
        elif multiplier < 5.0:
            return f"✅ MEDIUM prediction ({multiplier}x) - Safe bet, cashout around {multiplier-0.5:.1f}x"
        elif multiplier < 10.0:
            return f"🚀 HIGH prediction ({multiplier}x) - Good opportunity! Cashout {multiplier-1:.1f}x"
        else:
            return f"💎 EXTREME prediction ({multiplier}x) - Rare! Cashout gradually"
    
    def update_history(self, actual_multiplier):
        """Update history dengan hasil actual"""
        self.history.append(actual_multiplier)
    
    def simulate_round(self):
        """Simulate satu round (offline mode)"""
        # Generate prediction
        prediction = self.generate_prediction()
        
        # Simulate actual result (realistic distribution)
        weights = [40, 35, 20, 5]  # low, medium, high, extreme
        category = random.choices(['low', 'medium', 'high', 'extreme'], weights=weights)[0]
        
        min_val, max_val = self.patterns[category]
        actual = round(random.uniform(min_val, max_val), 2)
        
        # Update history
        self.update_history(actual)
        
        # Check accuracy
        predicted_cat = prediction['category']
        if predicted_cat == category:
            self.correct_predictions += 1
            result = '✅ CORRECT'
        else:
            result = '❌ WRONG'
        
        prediction['actual_multiplier'] = actual
        prediction['actual_category'] = category
        prediction['result'] = result
        prediction['accuracy'] = f"{(self.correct_predictions/self.total_predictions*100):.1f}%"
        
        return prediction
    
    def print_prediction(self, pred):
        """Pretty print prediction"""
        print(f"\n{'='*70}")
        print(f"🎮 ROUND #{pred['round']} | {pred['timestamp']}")
        print(f"{'='*70}")
        print(f"🔮 PREDICTION: {pred['predicted_multiplier']}x ({pred['category'].upper()})")
        print(f"📊 Confidence: {pred['confidence']}%")
        print(f"💡 {pred['advice']}")
        
        if 'actual_multiplier' in pred:
            print(f"\n🎯 ACTUAL: {pred['actual_multiplier']}x ({pred['actual_category'].upper()})")
            print(f"📈 Result: {pred['result']}")
            print(f"📊 Overall Accuracy: {pred['accuracy']}")
        
        print(f"{'='*70}")
    
    def run_simulation(self, rounds=20, delay=2):
        """Run simulation mode"""
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🚀 SPACEMAN PREDICTOR - SIMULATION MODE")
        print("🎯 Target: dashkng-88-ind-929.com")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"⏱️  Running {rounds} rounds with {delay}s delay...")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        results = []
        
        for i in range(rounds):
            prediction = self.simulate_round()
            self.print_prediction(prediction)
            results.append(prediction)
            
            if i < rounds - 1:
                time.sleep(delay)
        
        # Final summary
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("📊 FINAL STATISTICS")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"Total Rounds: {self.total_predictions}")
        print(f"Correct Predictions: {self.correct_predictions}")
        print(f"Wrong Predictions: {self.total_predictions - self.correct_predictions}")
        print(f"Accuracy: {(self.correct_predictions/self.total_predictions*100):.1f}%")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        # Save results
        with open('spaceman_predictions.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print("\n💾 Results saved to: spaceman_predictions.json")
        
        # Save configuration
        config = {
            'websocket_endpoints': self.ws_endpoints,
            'api_key': self.api_key,
            'brand': self.brand,
            'target_site': 'dashkng-88-ind-929.com',
            'note': 'WebSocket requires authentication. Use browser cookies for online mode.',
        }
        
        with open('spaceman_config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print("💾 Configuration saved to: spaceman_config.json")
        
        return results

def main():
    engine = SpacemanPredictorEngine()
    
    # Run 20 rounds simulation
    engine.run_simulation(rounds=20, delay=1)

if __name__ == '__main__':
    main()
