import sqlite3

def init_leetcode_db():
    """Initializes a dedicated database file exclusively for LeetCode DSA questions."""
    connection = sqlite3.connect("leetcode_coding.db")
    cursor = connection.cursor()
    
    cursor.execute('DROP TABLE IF EXISTS leetcode_vault;')
    
    cursor.execute('''
        CREATE TABLE leetcode_vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_tier TEXT,
            role_name TEXT,
            question_title TEXT,
            difficulty TEXT,
            leetcode_url TEXT
        )
    ''')
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lc_core ON leetcode_vault(company_tier, role_name);")
    connection.commit()
    connection.close()
    print("✓ Dedicated 'leetcode_coding.db' initialized cleanly with optimized search indexing.")

def seed_leetcode_questions():
    """Ingests exactly 150 premium LeetCode DSA questions universally cross-mapped across all matrices."""
    
    # 1. BACKEND SOFTWARE ENGINEER (25 Questions)
    backend_problems = [
        ("Two Sum (#1)", "Easy", "https://leetcode.com/problems/two-sum/"),
        ("LRU Cache (#146)", "Hard", "https://leetcode.com/problems/lru-cache/"),
        ("Longest Substring Without Repeating Characters (#3)", "Medium", "https://leetcode.com/problems/longest-substring-without-repeating-characters/"),
        ("Merge k Sorted Lists (#23)", "Hard", "https://leetcode.com/problems/merge-k-sorted-lists/"),
        ("Linked List Cycle (#141)", "Easy", "https://leetcode.com/problems/linked-list-cycle/"),
        ("Container With Most Water (#11)", "Medium", "https://leetcode.com/problems/container-with-most-water/"),
        ("Trapping Rain Water (#42)", "Hard", "https://leetcode.com/problems/trapping-rain-water/"),
        ("Merge Intervals (#56)", "Medium", "https://leetcode.com/problems/merge-intervals/"),
        ("Valid Parentheses (#20)", "Easy", "https://leetcode.com/problems/valid-parentheses/"),
        ("Min Stack (#155)", "Medium", "https://leetcode.com/problems/min-stack/"),
        ("Decode String (#394)", "Medium", "https://leetcode.com/problems/decode-string/"),
        ("Binary Tree Maximum Path Sum (#124)", "Hard", "https://leetcode.com/problems/binary-tree-maximum-path-sum/"),
        ("Validate Binary Search Tree (#98)", "Medium", "https://leetcode.com/problems/validate-binary-search-tree/"),
        ("Number of Islands (#200)", "Medium", "https://leetcode.com/problems/number-of-islands/"),
        ("Word Search (#79)", "Medium", "https://leetcode.com/problems/word-search/"),
        ("Course Schedule (#207)", "Medium", "https://leetcode.com/problems/course-schedule/"),
        ("Product of Array Except Self (#238)", "Medium", "https://leetcode.com/problems/product-of-array-except-self/"),
        ("Kth Largest Element in an Array (#215)", "Medium", "https://leetcode.com/problems/kth-largest-element-in-an-array/"),
        ("Find Median from Data Stream (#295)", "Hard", "https://leetcode.com/problems/find-median-from-data-stream/"),
        ("Longest Increasing Subsequence (#300)", "Medium", "https://leetcode.com/problems/longest-increasing-subsequence/"),
        ("Coin Change (#322)", "Medium", "https://leetcode.com/problems/coin-change/"),
        ("Edit Distance (#72)", "Hard", "https://leetcode.com/problems/edit-distance/"),
        ("Subarray Sum Equals K (#560)", "Medium", "https://leetcode.com/problems/subarray-sum-equals-k/"),
        ("Top K Frequent Elements (#347)", "Medium", "https://leetcode.com/problems/top-k-frequent-elements/"),
        ("Sliding Window Maximum (#239)", "Hard", "https://leetcode.com/problems/sliding-window-maximum/")
    ]
    
    # 2. DATA SCIENTIST / MACHINE LEARNING ENGINEER (25 Questions)
    ds_ml_problems = [
        ("Median of Two Sorted Arrays (#4)", "Hard", "https://leetcode.com/problems/median-of-two-sorted-arrays/"),
        ("Majority Element (#169)", "Easy", "https://leetcode.com/problems/majority-element/"),
        ("Best Time to Buy and Sell Stock (#121)", "Easy", "https://leetcode.com/problems/best-time-to-buy-and-sell-stock/"),
        ("Max Points on a Line (#149)", "Hard", "https://leetcode.com/problems/max-points-on-a-line/"),
        ("Pow(x, n) (#50)", "Medium", "https://leetcode.com/problems/powx-n/"),
        ("Sqrt(x) (#69)", "Easy", "https://leetcode.com/problems/sqrtx/"),
        ("Single Number (#136)", "Easy", "https://leetcode.com/problems/single-number/"),
        ("Subsets (#78)", "Medium", "https://leetcode.com/problems/subsets/"),
        ("Permutations (#46)", "Medium", "https://leetcode.com/problems/permutations/"),
        ("Merge Sorted Array (#88)", "Easy", "https://leetcode.com/problems/merge-sorted-array/"),
        ("Sort Colors (#75)", "Medium", "https://leetcode.com/problems/sort-colors/"),
        ("Search a 2D Matrix (#74)", "Medium", "https://leetcode.com/problems/search-a-2d-matrix/"),
        ("Find Peak Element (#162)", "Medium", "https://leetcode.com/problems/find-peak-element/"),
        ("Climbing Stairs (#70)", "Easy", "https://leetcode.com/problems/climbing-stairs/"),
        ("House Robber (#198)", "Medium", "https://leetcode.com/problems/house-robber/"),
        ("K Closest Points to Origin (#973)", "Medium", "https://leetcode.com/problems/k-closest-points-to-origin/"),
        ("Task Scheduler (#621)", "Medium", "https://leetcode.com/problems/task-scheduler/"),
        ("Random Pick with Weight (#528)", "Medium", "https://leetcode.com/problems/random-pick-with-weight/"),
        ("Maximum Product Subarray (#152)", "Medium", "https://leetcode.com/problems/maximum-product-subarray/"),
        ("Missing Number (#268)", "Easy", "https://leetcode.com/problems/missing-number/"),
        ("Valid Anagram (#242)", "Easy", "https://leetcode.com/problems/valid-anagram/"),
        ("Group Anagrams (#49)", "Medium", "https://leetcode.com/problems/group-anagrams/"),
        ("Happy Number (#202)", "Easy", "https://leetcode.com/problems/happy-number/"),
        ("Spiral Matrix (#54)", "Medium", "https://leetcode.com/problems/spiral-matrix/"),
        ("Rotate Image (#48)", "Medium", "https://leetcode.com/problems/rotate-image/")
    ]
    
    # 3. FRONTEND WEB DEVELOPER (25 Questions)
    frontend_problems = [
        ("Valid Palindrome (#125)", "Easy", "https://leetcode.com/problems/valid-palindrome/"),
        ("Is Subsequence (#392)", "Easy", "https://leetcode.com/problems/is-subsequence/"),
        ("3Sum (#15)", "Medium", "https://leetcode.com/problems/3sum/"),
        ("Minimum Size Subarray Sum (#209)", "Medium", "https://leetcode.com/problems/minimum-size-subarray-sum/"),
        ("Reverse Words in a String (#151)", "Medium", "https://leetcode.com/problems/reverse-words-in-a-string/"),
        ("Valid Sudoku (#36)", "Medium", "https://leetcode.com/problems/valid-sudoku/"),
        ("Set Matrix Zeroes (#73)", "Medium", "https://leetcode.com/problems/set-matrix-zeroes/"),
        ("Ransom Note (#383)", "Easy", "https://leetcode.com/problems/ransom-note/"),
        ("Word Pattern (#290)", "Easy", "https://leetcode.com/problems/word-pattern/"),
        ("Longest Consecutive Sequence (#128)", "Medium", "https://leetcode.com/problems/longest-consecutive-sequence/"),
        ("Simplify Path (#71)", "Medium", "https://leetcode.com/problems/simplify-path/"),
        ("Evaluate Reverse Polish Notation (#150)", "Medium", "https://leetcode.com/problems/evaluate-reverse-polish-notation/"),
        ("Remove Nth Node From End of List (#19)", "Medium", "https://leetcode.com/problems/remove-nth-node-from-end-of-list/"),
        ("Merge Two Sorted Lists (#21)", "Easy", "https://leetcode.com/problems/merge-two-sorted-lists/"),
        ("Invert Binary Tree (#226)", "Easy", "https://leetcode.com/problems/invert-binary-tree/"),
        ("Maximum Depth of Binary Tree (#104)", "Easy", "https://leetcode.com/problems/maximum-depth-of-binary-tree/"),
        ("Binary Tree Level Order Traversal (#102)", "Medium", "https://leetcode.com/problems/binary-tree-level-order-traversal/"),
        ("Lowest Common Ancestor of a Binary Tree (#236)", "Medium", "https://leetcode.com/problems/lowest-common-ancestor-of-a-binary-tree/"),
        ("Letter Combinations of a Phone Number (#17)", "Medium", "https://leetcode.com/problems/letter-combinations-of-a-phone-number/"),
        ("Generate Parentheses (#22)", "Medium", "https://leetcode.com/problems/generate-parentheses/"),
        ("Search Insert Position (#35)", "Easy", "https://leetcode.com/problems/search-insert-position/"),
        ("First Bad Version (#278)", "Easy", "https://leetcode.com/problems/first-bad-version/"),
        ("Flatten Binary Tree to Linked List (#114)", "Medium", "https://leetcode.com/problems/flatten-binary-tree-to-linked-list/"),
        ("Zigzag Conversion (#6)", "Medium", "https://leetcode.com/problems/zigzag-conversion/"),
        ("Length of Last Word (#58)", "Easy", "https://leetcode.com/problems/length-of-last-word/")
    ]

    # 4. DEVOPS / CLOUD ENGINEER (25 Questions)
    devops_problems = [
        ("Network Delay Time (#743)", "Medium", "https://leetcode.com/problems/network-delay-time/"),
        ("Min Cost to Connect All Points (#1584)", "Medium", "https://leetcode.com/problems/min-cost-to-connect-all-points/"),
        ("Cheapest Flights Within K Stops (#787)", "Medium", "https://leetcode.com/problems/cheapest-flights-within-k-stops/"),
        ("Is Graph Bipartite? (#785)", "Medium", "https://leetcode.com/problems/is-graph-bipartite/"),
        ("Clone Graph (#133)", "Medium", "https://leetcode.com/problems/clone-graph/"),
        ("Maximal Square (#221)", "Medium", "https://leetcode.com/problems/maximal-square/"),
        ("Daily Temperatures (#739)", "Medium", "https://leetcode.com/problems/daily-temperatures/"),
        ("Sliding Window Maximum (#239)", "Hard", "https://leetcode.com/problems/sliding-window-maximum/"),
        ("Next Greater Element I (#496)", "Easy", "https://leetcode.com/problems/next-greater-element-i/"),
        ("Implement Queue using Stacks (#232)", "Easy", "https://leetcode.com/problems/implement-queue-using-stacks/"),
        ("Asteroid Collision (#735)", "Medium", "https://leetcode.com/problems/asteroid-collision/"),
        ("Open the Lock (#752)", "Medium", "https://leetcode.com/problems/open-the-lock/"),
        ("Rotting Oranges (#994)", "Medium", "https://leetcode.com/problems/rotting-oranges/"),
        ("Find Eventual Safe States (#802)", "Medium", "https://leetcode.com/problems/find-eventual-safe-states/"),
        ("All Paths From Source to Target (#797)", "Medium", "https://leetcode.com/problems/all-paths-from-source-to-target/"),
        ("Keys and Rooms (#841)", "Medium", "https://leetcode.com/problems/keys-and-rooms/"),
        ("Number of Connected Components (#323)", "Medium", "https://leetcode.com/problems/number-of-connected-components/"),
        ("Graph Valid Tree (#261)", "Medium", "https://leetcode.com/problems/graph-valid-tree/"),
        ("Redundant Connection (#684)", "Medium", "https://leetcode.com/problems/redundant-connection/"),
        ("Satisfiability of Equality Equations (#990)", "Medium", "https://leetcode.com/problems/satisfiability-of-equality-equations/"),
        ("Longest Common Subsequence (#1143)", "Medium", "https://leetcode.com/problems/longest-common-subsequence/"),
        ("Unique Paths (#62)", "Medium", "https://leetcode.com/problems/unique-paths/"),
        ("Minimum Path Sum (#64)", "Medium", "https://leetcode.com/problems/minimum-path-sum/"),
        ("Jump Game (#55)", "Medium", "https://leetcode.com/problems/jump-game/"),
        ("Gas Station (#134)", "Medium", "https://leetcode.com/problems/gas-station/")
    ]

    # 5. CYBERSECURITY ANALYST (25 Questions)
    cyber_problems = [
        ("Counting Bits (#338)", "Easy", "https://leetcode.com/problems/counting-bits/"),
        ("Number of 1 Bits (#191)", "Easy", "https://leetcode.com/problems/number-of-1-bits/"),
        ("Reverse Bits (#190)", "Easy", "https://leetcode.com/problems/reverse-bits/"),
        ("Bitwise AND of Numbers Range (#201)", "Medium", "https://leetcode.com/problems/bitwise-and-of-numbers-range/"),
        ("IP to CIDR (#751)", "Easy", "https://leetcode.com/problems/ip-to-cidr/"),
        ("Validate IP Address (#468)", "Medium", "https://leetcode.com/problems/validate-ip-address/"),
        ("UTF-8 Validation (#393)", "Medium", "https://leetcode.com/problems/utf-8-validation/"),
        ("Encode and Decode Strings (#271)", "Medium", "https://leetcode.com/problems/encode-and-decode-strings/"),
        ("Repeated DNA Sequences (#187)", "Medium", "https://leetcode.com/problems/repeated-dna-sequences/"),
        ("Permutation in String (#567)", "Medium", "https://leetcode.com/problems/permutation-in-string/"),
        ("Find All Anagrams in a String (#438)", "Medium", "https://leetcode.com/problems/find-all-anagrams-in-a-string/"),
        ("Minimum Window Substring (#76)", "Hard", "https://leetcode.com/problems/minimum-window-substring/"),
        ("String to Integer (atoi) (#8)", "Medium", "https://leetcode.com/problems/string-to-integer-atoi/"),
        ("Valid Number (#65)", "Hard", "https://leetcode.com/problems/valid-number/"),
        ("Implement Trie (Prefix Tree) (#208)", "Medium", "https://leetcode.com/problems/implement-trie-prefix-tree/"),
        ("Design Add and Search Words Data Structure (#211)", "Medium", "https://leetcode.com/problems/design-add-and-search-words-data-structure/"),
        ("Word Search II (#212)", "Hard", "https://leetcode.com/problems/word-search-ii/"),
        ("Palindromic Substrings (#647)", "Medium", "https://leetcode.com/problems/palindromic-substrings/"),
        ("Longest Palindromic Substring (#5)", "Medium", "https://leetcode.com/problems/longest-palindromic-substring/"),
        ("Regular Expression Matching (#10)", "Hard", "https://leetcode.com/problems/regular-expression-matching/"),
        ("Basic Calculator (#224)", "Hard", "https://leetcode.com/problems/basic-calculator/"),
        ("Path Sum II (#113)", "Medium", "https://leetcode.com/problems/path-sum-ii/"),
        ("Sum Root to Leaf Numbers (#129)", "Medium", "https://leetcode.com/problems/sum-root-to-leaf-numbers/"),
        ("Subsets II (#90)", "Medium", "https://leetcode.com/problems/subsets-ii/"),
        ("N-Queens (#51)", "Hard", "https://leetcode.com/problems/n-queens/")
    ]

    # 6. UI/UX DESIGNER (25 Questions)
    uiux_problems = [
        ("Design Twitter (#355)", "Medium", "https://leetcode.com/problems/design-twitter/"),
        ("Design Underground System (#1396)", "Medium", "https://leetcode.com/problems/design-underground-system/"),
        ("Flatten Nested List Iterator (#341)", "Medium", "https://leetcode.com/problems/flatten-nested-list-iterator/"),
        ("Peeking Iterator (#284)", "Medium", "https://leetcode.com/problems/peeking-iterator/"),
        ("Design Browser History (#1472)", "Medium", "https://leetcode.com/problems/design-browser-history/"),
        ("Design Parking System (#1603)", "Easy", "https://leetcode.com/problems/design-parking-system/"),
        ("Design Authentication Manager (#1797)", "Medium", "https://leetcode.com/problems/design-authentication-manager/"),
        ("Insert Delete GetRandom O(1) (#380)", "Medium", "https://leetcode.com/problems/insert-delete-getrandom-o1/"),
        ("Design Linked List (#707)", "Medium", "https://leetcode.com/problems/design-linked-list/"),
        ("Design HashMap (#706)", "Easy", "https://leetcode.com/problems/design-hashmap/"),
        ("Design HashSet (#705)", "Easy", "https://leetcode.com/problems/design-hashset/"),
        ("Implement Stack using Queues (#225)", "Easy", "https://leetcode.com/problems/implement-stack-using-queues/"),
        ("Moving Average from Data Stream (#346)", "Easy", "https://leetcode.com/problems/moving-average-from-data-stream/"),
        ("Design Circular Queue (#622)", "Medium", "https://leetcode.com/problems/design-circular-queue/"),
        ("Design Front Middle Back Queue (#1670)", "Medium", "https://leetcode.com/problems/design-front-middle-back-queue/"),
        ("Binary Tree Zigzag Level Order Traversal (#103)", "Medium", "https://leetcode.com/problems/binary-tree-zigzag-level-order-traversal/"),
        ("Binary Tree Right Side View (#199)", "Medium", "https://leetcode.com/problems/binary-tree-right-side-view/"),
        ("Average of Levels in Binary Tree (#637)", "Easy", "https://leetcode.com/problems/average-of-levels-in-binary-tree/"),
        ("Populating Next Right Pointers in Each Node (#116)", "Medium", "https://leetcode.com/problems/populating-next-right-pointers-in-each-node/"),
        ("Merge Strings Alternately (#1768)", "Easy", "https://leetcode.com/problems/merge-strings-alternately/"),
        ("Reverse String (#344)", "Easy", "https://leetcode.com/problems/reverse-string/"),
        ("Fizz Buzz (#412)", "Easy", "https://leetcode.com/problems/fizz-buzz/"),
        ("Fibonacci Number (#509)", "Easy", "https://leetcode.com/problems/fibonacci-number/"),
        ("Pascal's Triangle (#118)", "Easy", "https://leetcode.com/problems/pascals-triangle/"),
        ("Array Partition (#561)", "Easy", "https://leetcode.com/problems/array-partition/")
    ]

    connection = sqlite3.connect("leetcode_coding.db")
    cursor = connection.cursor()
    total_inserted = 0
    
    # Target companies cross-section footprint list
    all_companies = ["Google", "Microsoft", "Amazon", "TCS", "Infosys", "Wipro", "Accenture"]
    
    # Map each array cleanly to its respective profile tag
    master_role_map = {
        "Backend Software Engineer": backend_problems,
        "Data Scientist / Machine Learning Engineer": ds_ml_problems,
        "Frontend Web Developer": frontend_problems,
        "DevOps / Cloud Engineer": devops_problems,
        "Cybersecurity Analyst": cyber_problems,
        "UI/UX Designer": uiux_problems
    }
    
    # Universal loop matrix executing allocations safely
    print("[Ingestion Core] universally seeding 150 LeetCode problems across all target layers...")
    for company in all_companies:
        for role, dataset in master_role_map.items():
            for title, diff, url in dataset:
                cursor.execute('''
                    INSERT INTO leetcode_vault (company_tier, role_name, question_title, difficulty, leetcode_url) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (company, role, title, diff, url))
                total_inserted += 1

    connection.commit()
    connection.close()
    print(f"🚀 SUCCESS: Mapped out and seeded exactly {total_inserted} rows into 'leetcode_coding.db'.")

if __name__ == "__main__":
    init_leetcode_db()
    seed_leetcode_questions()