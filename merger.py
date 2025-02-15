#!/usr/bin/env python3
"""
Functions to merge csv files
"""

import pandas as pd
from fuzzywuzzy import process, fuzz

# reads csv files
colors_used = pd.read_csv('csv/Colors_Used.csv')
subject_matter = pd.read_csv('csv/Subject_Matter.csv')
episode_dates = pd.read_csv('csv/Episode_Dates.csv')


# preprocess titles
def preprocess_title(title):
    return (''.join(title.lower().split()))


# preprocess titles for matching
colors_used['processed_painting_title'] = \
    colors_used['painting_title'].apply(preprocess_title)
subject_matter['processed_TITLE'] = \
    subject_matter['TITLE'].apply(preprocess_title)
episode_dates['processed_Episode_TITLE'] = \
    episode_dates['Episode_TITLE'].apply(preprocess_title)


# fuzzy matching with unique matching
def fuzzy_merge(df_1, df_2, key1, key2,
                processed_key1, processed_key2,
                threshold=60, limit=1
                ):
    """
    Fuzzy matching of two DataFrames on a given key.
    df_1: DataFrame 1
    df_2: DataFrame 2
    key1: original key column of df_1
    key2: original key column of df_2
    processed_key1: processed key column of df_1
    processed_key2: processed key column of df_2
    threshold: matching threshold
    limit: max number of matches
    """

    s = df_2[processed_key2].tolist()
    matches = df_1[processed_key1].apply(
        lambda x: process.extract(
            x, s, limit=limit, scorer=fuzz.token_set_ratio
        )
    )

    df_1['matches'] = matches
    df_1['best_match'] = df_1['matches'].apply(
        lambda x: (
            df_2.iloc[s.index(x[0][0])][key2]
            if x and x[0][1] >= threshold
            else None)
    )
    df_1['match_score'] = df_1['matches'].apply(lambda x: x[0][1] if x else 0)

    return (df_1.drop(columns=['matches']))


# merge DataFrames uniquely
def unique_merge(df_1, df_2, key1, key2, processed_key1, processed_key2):
    """
    Merge two df based on best fuzzy matches.
    """
    # fuzzy merge
    df_1 = fuzzy_merge(df_1, df_2, key1, key2, processed_key1, processed_key2)

    # merge based on best matches
    merged_df = df_1.merge(df_2, left_on='best_match',
                           right_on=key2, how='left', suffixes=('', '_subject')
                           )

    # drop intermediate columns
    merged_df = merged_df.drop(columns=['best_match', 'match_score'])

    return (merged_df)


# merge Colors_Used with Subject_Matter uniquely
merged_df = unique_merge(colors_used,
                         subject_matter,
                         'painting_title',
                         'TITLE',
                         'processed_painting_title',
                         'processed_TITLE'
                         )

# checkes if processed columns are present
merged_df['processed_painting_title'] = \
    merged_df['painting_title'].apply(preprocess_title)

# Merge the result with Episode_Dates uniquely
merged_df = unique_merge(merged_df, episode_dates,
                         'painting_title',
                         'Episode_TITLE',
                         'processed_painting_title',
                         'processed_Episode_TITLE'
                         )


# keep only one entry per season for each title
def filter_season_duplicates(df, key_col, season_col):
    """
    Filter out duplicate entries for each title per season.
    """
    # remove exact duplicates first
    df = df.drop_duplicates(subset=[key_col, season_col])

    # keep one entry per title per season
    df_filtered = df.groupby([key_col, season_col], as_index=False).first()

    return (df_filtered)


merged_df = filter_season_duplicates(merged_df, 'painting_title', 'season')

# sort by season and episode
merged_df = \
    merged_df.sort_values(by=['season', 'episode']).reset_index(drop=True)

# drop unnecessary columns
columns_to_drop = ['processed_painting_title',
                   'processed_TITLE',
                   'processed_Episode_TITLE']
merged_df = merged_df.drop(columns=columns_to_drop, errors='ignore')

# save to csv
merged_df.to_csv('csv/Merged_Output.csv', index=False, header=True)

print("Merged csv created successfully.")
