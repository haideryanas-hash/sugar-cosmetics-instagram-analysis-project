"""
Sugar Cosmetics Instagram Performance Analytics - data preprocessing.

Input : sugar_cosmetics_instagram_data.csv
Output: sugar_cosmetics_instagram_cleaned.csv   (one row per post, with calculated fields)
        sugar_cosmetics_hashtags_long.csv       (one row per post-hashtag, for hashtag analysis)

Run:  python preprocess_sugar_cosmetics.py
Needs: pandas, openpyxl
"""
import os
import pandas as pd

INPUT_FILE = "sugar_cosmetics_instagram_data.csv"
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------- 1. LOAD
df = pd.read_csv(INPUT_FILE)
print("Shape (rows, columns):", df.shape)

# Tableau dislikes spaces in names, so use underscores: "Post Date" -> "Post_Date"
df.columns = [c.strip().replace(" ", "_") for c in df.columns]
print("Columns:", list(df.columns))

# ------------------------------------------------- 2. DATA QUALITY CHECKS
print("\n--- Data types ---")
print(df.dtypes)

print("\n--- Missing values per column (expected: 0) ---")
print(df.isnull().sum())

print("\nExact duplicate rows (expected: 0):", df.duplicated().sum())

num_cols = df.select_dtypes(include="number").columns
print("\n--- Zero values (valid counts, do NOT replace; expected: Shares 9, Follows 1) ---")
zeros = (df[num_cols] == 0).sum()
print(zeros[zeros > 0])

print("\nNegative values in numeric columns (expected: 0):", int((df[num_cols] < 0).sum().sum()))

# Date validity
df["Post_Date"] = pd.to_datetime(df["Post_Date"], errors="coerce")
print("\nInvalid dates:", df["Post_Date"].isnull().sum())
print("Date range:", df["Post_Date"].min().date(), "to", df["Post_Date"].max().date())

# Category consistency (look for spelling variants)
for col in ["Post_Type", "Campaign_Type", "Audience_Emotion", "Engagement_Source"]:
    print(f"\n{col}:\n{df[col].value_counts()}")

# Business-logic validation
print("\nRows where Reach > Impressions (expected: 0):", (df["Reach"] > df["Impressions"]).sum())
print("Rows where Follows > Profile_Visits (expected: 0):", (df["Follows"] > df["Profile_Visits"]).sum())
print("Rows where Reach = 0 (expected: 0):", (df["Reach"] == 0).sum())

# No missing values or duplicates, so no imputation or row deletion is needed.

# ------------------------------------------- 3. TIDY TEXT COLUMNS
for col in ["Post_Type", "Campaign_Type", "Audience_Emotion", "Engagement_Source", "Hashtags"]:
    df[col] = df[col].astype(str).str.strip()

# ------------------------------------------ 4. CALCULATED FIELDS / KPIs
# Post_ID: the file has no unique ID, so create one (needed to join the hashtag table)
df.insert(0, "Post_ID", range(1, len(df) + 1))

# Total interactions (project-specific definition, not Instagram's official one)
df["Engagement"] = df["Likes"] + df["Comments"] + df["Shares"] + df["Saves"]

# Engagement rate by reach, stored as a fraction (0.18 = 18%).
# In Tableau format it as Percentage. Reach is always > 0 here, so no divide-by-zero guard is needed.
df["Engagement_Rate"] = df["Engagement"] / df["Reach"]

df["Month_Year"] = df["Post_Date"].dt.strftime("%Y-%m")
df["Weekday"] = df["Post_Date"].dt.day_name()
df["Hashtag_Count"] = df["Hashtags"].str.count(",") + 1

# Exploratory KPIs (not confirmed conversion rates until attribution rules are verified)
df["Follow_Rate"] = df["Follows"] / df["Profile_Visits"]   # follows per profile visit
df["Reach_Rate"] = df["Reach"] / df["Impressions"]         # reach per impression

# --------------------------------------------- 5. HASHTAGS: ONE ROW EACH
hashtags_long = (
    df[["Post_ID", "Hashtags", "Engagement_Rate", "Reach", "Likes", "Follows"]]
    .assign(Hashtag=lambda x: x["Hashtags"].str.split(","))
    .explode("Hashtag")
    .assign(Hashtag=lambda x: x["Hashtag"].str.strip())
    .drop(columns="Hashtags")[["Post_ID", "Hashtag", "Engagement_Rate", "Reach", "Likes", "Follows"]]
)

# ------------------------------------------------------ 6. SANITY CHECK
print("\n--- Summary ---")
print("Total posts:", len(df))
print("Total likes:", f"{df['Likes'].sum():,}")
print("Total comments:", f"{df['Comments'].sum():,}")
print("Summed reach:", f"{df['Reach'].sum():,}")
print("Average engagement rate:", f"{df['Engagement_Rate'].mean():.2%}")
print("Distinct hashtags:", sorted(hashtags_long["Hashtag"].unique()))

# ------------------------------------------------------------- 7. EXPORT
df.to_csv(os.path.join(OUTPUT_DIR, "sugar_cosmetics_instagram_cleaned.csv"), index=False)
hashtags_long.to_csv(os.path.join(OUTPUT_DIR, "sugar_cosmetics_hashtags_long.csv"), index=False)
print(f"\nSaved 2 CSV files in ./{OUTPUT_DIR}/")
