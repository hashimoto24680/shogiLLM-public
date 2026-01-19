
import json
import glob
import os
from collections import Counter

def analyze_comment_lengths(input_dir, threshold=100):
    json_files = glob.glob(os.path.join(input_dir, "*.json"))
    total_entries = 0
    long_comments = 0
    length_dist = Counter()
    
    print(f"Checking {len(json_files)} files in {input_dir}...")
    
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for entry in data:
                    total_entries += 1
                    comment = entry.get('comment', '')
                    length = len(comment)
                    
                    if length >= threshold:
                        long_comments += 1
                    
                    # 分布用（50文字刻み）
                    bucket = (length // 50) * 50
                    length_dist[bucket] += 1
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            
    print(f"\nTotal entries: {total_entries}")
    print(f"Entries with comment >= {threshold} chars: {long_comments} ({long_comments/total_entries*100:.1f}%)")
    
    print("\nLength Distribution:")
    for bucket in sorted(length_dist.keys()):
        range_str = f"{bucket}-{bucket+49}"
        count = length_dist[bucket]
        print(f"{range_str}: {count}")

if __name__ == "__main__":
    analyze_comment_lengths("data/kif_commentary_json", threshold=100)
