import pandas as pd
from io import StringIO
import warnings
warnings.filterwarnings('ignore')
import argparse



def post_process_annotation(json_path):
    df = pd.read_json(json_path)

    # Determine the maximum number of labels in any row
    max_labels = df['labels'].apply(lambda x: len([i for i in x if isinstance(i, str)])).max()

    # Clear any previous label or index columns if rerunning this cell in your environment
    for col in [c for c in df.columns if c.startswith('label_') or c in ['start_index', 'end_index']]:
        del df[col]

    # Split 'labels' into separate columns for labels and indexes
    for i in range(1, max_labels + 1):
        df[f'label_{i}'] = df['labels'].apply(lambda x: [i for i in x if isinstance(i, str)][i-1] if len([i for i in x if isinstance(i, str)]) >= i else None)

    # Extract start and end index
    df['start_index'] = df['labels'].apply(lambda x: [i for i in x if isinstance(i, int)][0] if len([i for i in x if isinstance(i, int)]) > 0 else None)
    df['end_index'] = df['labels'].apply(lambda x: [i for i in x if isinstance(i, int)][1] if len([i for i in x if isinstance(i, int)]) > 0 else None)

    # Remove a list-format column (useless)
    df = df.drop(['labels'], axis=1)

    # Move index columns to the front

    start_idx = df.pop('start_index')
    df.insert(2, 'start_index', start_idx)
    end_idx = df.pop('end_index')
    df.insert(3, 'end_index', end_idx)

    return df 


def main():

    """
    For example, type the following in your command
        `python postprocess_daily.py --name minhwa --path 'minhwa.json' --start 1000 --end 1500` 

    """

    parser = argparse.ArgumentParser()

    # Add an argument
    parser.add_argument('--name', type=str, required=True)
    parser.add_argument('--path', type=str, required=True)
    parser.add_argument('--start', type=int, required=True)
    parser.add_argument('--end', type=int, required=True)

    # Parse the argument
    args = parser.parse_args()
    print('File Path: ', args.path)

    df = post_process_annotation(args.path)

    df.loc[(df.start_index > args.start)& (df.end_index < args.end)].to_csv(f"{args.name}.csv", index=False)


main()