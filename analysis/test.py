import pandas as pd

# Example DataFrame
data = {
    "before": ["A", "B", "C", "D"],
    "after": ["B", "C", "E", "F"]
}
df = pd.DataFrame(data)

def chain_with_join(df):
    # Start with the original DataFrame
    current_df = df.copy()
    chains = []

    while not current_df.empty:
        # Perform a self-join on 'after' and 'before'
        extended_df = current_df.merge(
            df, 
            left_on='after', 
            right_on='before', 
            how='left', 
            suffixes=('_left', '_right')
        )

        # Create the new chains by combining columns
        extended_df['before'] = extended_df['before_left']
        extended_df['after'] = extended_df['after_right'].fillna(extended_df['after_left'])

        # Keep only the necessary columns
        extended_df = extended_df[['before', 'after']]

        # If no new rows are added, break
        if len(extended_df) == len(current_df):
            break

        current_df = extended_df
        print(current_df)
        raise Exception

    # Collect unique chains
    chains = []
    visited = set()
    for index, row in df.iterrows():
        if row['before'] not in visited:
            chain = [row['before']]
            current = row['after']
            visited.add(row['before'])
            while current and current not in visited:
                chain.append(current)
                visited.add(current)
                next_row = df[df['before'] == current]
                if next_row.empty:
                    break
                current = next_row.iloc[0]['after']
            chains.append(chain)

    return chains

chains = chain_with_join(df)
print(chains)
