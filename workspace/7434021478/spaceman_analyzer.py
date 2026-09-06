#!/usr/bin/env python3
"""
Spaceman Game Analyzer & Predictor
Phase 2: Reverse Engineering & Pattern Analysis
"""

import random
import time
import json
from datetime import datetime, timedelta

class SpacemanAnalyzer:
    def __init__(self):
        self.crash_history = []
        self.prediction_model = None
        
    def simulate_crash_data(self, rounds=200):
        """
        Simulate historical crash data untuk testing
        Real implementation bakal fetch dari actual game API
        """
        print("📊 Generating simulated crash data (placeholder for real API)...\n")
        
        for i in range(rounds):
            # Spaceman typically crashes between 1.00x - 100.00x
            # Distribution: most crashes 1.0-5.0x, rare high multipliers
            rand = random.random()
            if rand < 0.4:
                crash = round(random.uniform(1.0, 2.5), 2)
            elif rand < 0.7:
                crash = round(random.uniform(2.5, 5.0), 2)
            elif rand < 0.9:
                crash = round(random.uniform(5.0, 10.0), 2)
            else:
                crash = round(random.uniform(10.0, 100.0), 2)
            
            self.crash_history.append({
                'round': i + 1,
                'multiplier': crash,
                'timestamp': datetime.now() - timedelta(seconds=(rounds-i)*30)
            })
        
        print(f"✅ Generated {len(self.crash_history)} crash records")
        print(f"   Sample: {self.crash_history[-5:]}\n")
        
    def analyze_patterns(self):
        """
        Statistical analysis untuk cari pattern
        """
        print("🔍 Analyzing crash patterns...\n")
        
        multipliers = [r['multiplier'] for r in self.crash_history]
        
        avg = sum(multipliers) / len(multipliers)
        low_crashes = len([m for m in multipliers if m < 2.0])
        mid_crashes = len([m for m in multipliers if 2.0 <= m < 10.0])
        high_crashes = len([m for m in multipliers if m >= 10.0])
        
        print(f"Average crash multiplier: {avg:.2f}x")
        print(f"Low crashes (<2x): {low_crashes} ({low_crashes/len(multipliers)*100:.1f}%)")
        print(f"Mid crashes (2-10x): {mid_crashes} ({mid_crashes/len(multipliers)*100:.1f}%)")
        print(f"High crashes (>10x): {high_crashes} ({high_crashes/len(multipliers)*100:.1f}%)")
        print()
        
        return {
            'average': avg,
            'distribution': {
                'low': low_crashes / len(multipliers),
                'mid': mid_crashes / len(multipliers),
                'high': high_crashes / len(multipliers)
            }
        }
    
    def predict_next_crashes(self, hours=1):
        """
        Predict crashes untuk next N hours
        Based on statistical model (placeholder - real model perlu ML atau RNG reverse engineering)
        """
        print(f"🎯 Generating predictions for next {hours} hour(s)...\n")
        
        predictions = []
        current_time = datetime.now()
        rounds_per_hour = 120  # Assume 1 round per 30 seconds
        total_rounds = rounds_per_hour * hours
        
        for i in range(total_rounds):
            pred_time = current_time + timedelta(seconds=i*30)
            
            # Weighted random based on distribution analysis
            rand = random.random()
            if rand < 0.4:
                pred_multiplier = round(random.uniform(1.0, 2.5), 2)
            elif rand < 0.7:
                pred_multiplier = round(random.uniform(2.5, 5.0), 2)
            elif rand < 0.9:
                pred_multiplier = round(random.uniform(5.0, 10.0), 2)
            else:
                pred_multiplier = round(random.uniform(10.0, 50.0), 2)
            
            predictions.append({
                'time': pred_time.strftime('%Y-%m-%d %H:%M:%S'),
                'predicted_multiplier': pred_multiplier,
                'confidence': random.randint(65, 85)  # Simulated confidence score
            })
        
        print(f"✅ Generated {len(predictions)} predictions")
        print(f"   First 5 predictions:")
        for p in predictions[:5]:
            print(f"   {p['time']} → {p['predicted_multiplier']}x (confidence: {p['confidence']}%)")
        print()
        
        return predictions

if __name__ == "__main__":
    print("="*60)
    print("SPACEMAN GAME PREDICTOR - PHASE 2")
    print("="*60 + "\n")
    
    analyzer = SpacemanAnalyzer()
    
    # Step 1: Get historical data
    analyzer.simulate_crash_data(rounds=200)
    
    # Step 2: Analyze patterns
    stats = analyzer.analyze_patterns()
    
    # Step 3: Generate predictions
    predictions = analyzer.predict_next_crashes(hours=1)
    
    # Save predictions to JSON
    output_file = 'spaceman_predictions.json'
    with open(output_file, 'w') as f:
        json.dump(predictions, f, indent=2)
    
    print(f"💾 Predictions saved to {output_file}")
    print("\n[Ready for Phase 3: Web Dashboard Build]")
