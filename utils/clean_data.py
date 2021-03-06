def thres_score_range(df, max_scores):
    """
    Scores above max => max; scores below 0 => 0
        - df: pd.DataFrame() to be cleaned
        - max_scores: pd.DataFrame() containing max score for each question
        - Both dataframes should contain the same columns
    """
    for col in df:
        max_score = max_scores[col]
        df.loc[df[col] > max_score, col] = max_score
        df.loc[df[col] < 0, col] = 0
    return df.copy()
