import numpy as np
import pandas as pd
import os

import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.base import BaseEstimator, TransformerMixin

DATADIR = "input/"

def list_files(input_dir = "input/"):
    return (os.listdir(input_dir))

def read_dataset_csv(input_dir = "input/", file = "bureau.csv"):
    return (pd.read_csv(input_dir + file))

def read_train_test(input_dir = "input/", train_file = 'train.csv', test_file = 'test.csv'):
    train = pd.read_csv(input_dir + train_file)
    test = pd.read_csv(input_dir + test_file)
    return train, test

def get_memory_usage_mb(dataset):
    return (dataset.memory_usage().sum() / 1024 / 1024)

def check_missing(dataset):
    all_data_na_absolute = dataset.isnull().sum()
    all_data_na_percent = (dataset.isnull().sum() / len(dataset)) * 100
    mis_val_table = pd.concat([all_data_na_absolute, all_data_na_percent], axis=1)
    mis_val_table.rename(columns = {0 : 'Missing Values', 1 : '% of Total Values'}, inplace = True)
    missing_table = mis_val_table.drop(mis_val_table[mis_val_table.iloc[:, 1] == 0].index).sort_values('% of Total Values', ascending=False).round(2)
    return(missing_table)
    
def get_feature_groups(dataset):
    num_columns = list(dataset.select_dtypes(exclude=['object', 'category']).columns)
    cat_columns = list(dataset.select_dtypes(include=['object', 'category']).columns)
    return (num_columns, cat_columns)

def get_dtypes_columns(dataset):
    groups = dataset.columns.to_series().groupby(dataset.dtypes).groups
    return (groups)

def get_dtype_columns(dataset, dtypes = None):
    types_cols = get_dtypes_columns(dataset)
    if dtypes == None:
        list_columns = [list(cols) for tipo, cols in types_cols.items()]
    else:
        list_columns = [list(cols) for tipo, cols in types_cols.items() if tipo in dtypes]
    columns = []
    for cols in list_columns:
        columns += cols
    return(columns)

def get_missing_cols(dataset, dtypes = None):
    cols = get_dtype_columns(dataset, dtypes = dtypes)
    cols_null = [col for col in cols if dataset[col].isnull().any()]
    return (cols_null)

def get_categorical_missing_cols(dataset):
    cat_cols_null = get_missing_cols(dataset, dtypes = [np.dtype(object)])
    return (cat_cols_null)

def get_numerical_missing_cols(dataset):
    num_cols_null = get_missing_cols(dataset, dtypes = [np.dtype(np.int64), np.dtype(np.float64)])
    return (num_cols_null)

def add_columns_was_missing(X):
    cols_with_missing = [col for col in X.columns if X[col].isnull().any()]
    new_columns = []
    for col in cols_with_missing:
        new_col = col + '_was_missing'
        new_columns.append(new_col)
        X[new_col] = X[col].isnull()
    return X

def handle_missing_mode(X, mode_cols, group_by_cols = None):
        
    if group_by_cols == None:
        #X_ = X.copy()[mode_catcols]
        X_ = X.copy()
        for col in mode_cols:
            if X_[col].isnull().any():
                X_[col] = X_[col].transform(lambda x: x.fillna(x.mode()[0]))
    else:
        #X_ = X.copy()[mode_catcols + group_by_cols]
        X_ = X.copy()
        for col in mode_cols:
            if X_[col].isnull().any():
                X_[col] = X_.groupby(group_by_cols)[col].transform(lambda x: x.fillna(x.mode()[0]))
        
    return(X_)

def handle_missing_median(X, median_cols, group_by_cols = None):
        
    if group_by_cols == None:
        #X_ = X.copy()[mode_catcols]
        X_ = X.copy()
        for col in median_cols:
            if X_[col].isnull().any():
                X_[col] = X_[col].transform(lambda x: x.fillna(x.median()))
    else:
        #X_ = X.copy()[mode_catcols + group_by_cols]
        X_ = X.copy()
        for col in median_cols:
            if X_[col].isnull().any():
                X_[col] = X_.groupby(group_by_cols)[col].transform(lambda x: x.fillna(x.median()))
        
    return(X_)

class HandleMissingModeTransformer(BaseEstimator, TransformerMixin):
    def __init__(self):
        pass

    def transform(self, X, y=None):
        return handle_missing_mode(X, mode_catcols = self.cols)

    def fit(self, X, y=None):
        self.cols = get_categorical_missing_cols(X)
        return self
    
class HandleMissingMedianTransformer(BaseEstimator, TransformerMixin):
    def __init__(self):
        pass

    def transform(self, X, y=None):
        return handle_missing_median(X, median_cols = self.cols)

    def fit(self, X, y=None):
        self.cols = get_numerical_missing_cols(X)
        return self

def hot_encode(X, columns = None):
    if columns == None:
        return pd.get_dummies(X)
    else:
        return pd.get_dummies(X, columns = columns)
    
def correlation_target(dataset, target = "TARGET"):
    corr = dataset.corr()[target].sort_values(ascending = False)
    return(corr)
    
def correlation_matrix(dataset, target = 'TARGET', nvar = 10):
    corrmat = dataset.corr()
    cols = corrmat.nlargest(nvar + 1, target)[target].index
    cm = np.corrcoef(dataset[cols].values.T)
    sns.set(font_scale=1.25)
    sns.heatmap(cm, cbar=True, annot=True, square=True, fmt='.2f', 
                     annot_kws={'size': 10}, yticklabels=cols.values, xticklabels=cols.values)
    plt.show()
    return list(cols[1:])

def get_domain_knowledge_features(X):
    X_domain = X.copy()
    X_domain['CREDIT_INCOME_PERCENT'] = X_domain['AMT_CREDIT'] / X_domain['AMT_INCOME_TOTAL']
    X_domain['ANNUITY_INCOME_PERCENT'] = X_domain['AMT_ANNUITY'] / X_domain['AMT_INCOME_TOTAL']
    X_domain['CREDIT_TERM'] = X_domain['AMT_ANNUITY'] / X_domain['AMT_CREDIT']
    X_domain['DAYS_EMPLOYED_PERCENT'] = X_domain['DAYS_EMPLOYED'] / X_domain['DAYS_BIRTH']
    return (X_domain)

def agg_numeric(df, group_var, df_name):
    """Aggregates the numeric values in a dataframe. This can
    be used to create features for each instance of the grouping variable.
    
    Parameters
    --------
        df (dataframe): 
            the dataframe to calculate the statistics on
        group_var (string): 
            the variable by which to group df
        df_name (string): 
            the variable used to rename the columns
        
    Return
    --------
        agg (dataframe): 
            a dataframe with the statistics aggregated for 
            all numeric columns. Each instance of the grouping variable will have 
            the statistics (mean, min, max, sum; currently supported) calculated. 
            The columns are also renamed to keep track of features created.
    
    """
    # Remove id variables other than grouping variable
    for col in df:
        if col != group_var and 'SK_ID' in col:
            df = df.drop(columns = col)
            
    group_ids = df[group_var]
    numeric_df = df.select_dtypes(include = ['number'])
    numeric_df[group_var] = group_ids

    # Group by the specified variable and calculate the statistics
    agg = numeric_df.groupby(group_var).agg(['count', 'mean', 'max', 'min', 'sum']).reset_index()

    # Need to create new column names
    columns = [group_var]

    # Iterate through the variables names
    for var in agg.columns.levels[0]:
        # Skip the grouping variable
        if var != group_var:
            # Iterate through the stat names
            for stat in agg.columns.levels[1][:-1]:
                # Make a new column name for the variable and stat
                columns.append('%s_%s_%s' % (df_name, var, stat))

    agg.columns = columns
    return agg

def count_categorical(df, group_var, df_name):
    """Computes counts and normalized counts for each observation
    of `group_var` of each unique category in every categorical variable
    
    Parameters
    --------
    df : dataframe 
        The dataframe to calculate the value counts for.
        
    group_var : string
        The variable by which to group the dataframe. For each unique
        value of this variable, the final dataframe will have one row
        
    df_name : string
        Variable added to the front of column names to keep track of columns
    
    Return
    --------
    categorical : dataframe
        A dataframe with counts and normalized counts of each unique category in every categorical variable
        with one row for every unique value of the `group_var`.
        
    """
    
    # Select the categorical columns
    categorical = pd.get_dummies(df.select_dtypes(include = ['object']))

    # Make sure to put the identifying id on the column
    categorical[group_var] = df[group_var]

    # Groupby the group var and calculate the sum and mean
    categorical = categorical.groupby(group_var).agg(['sum', 'mean'])
    
    column_names = []
    
    # Iterate through the columns in level 0
    for var in categorical.columns.levels[0]:
        # Iterate through the stats in level 1
        for stat in ['count', 'count_norm']:
            # Make a new column name
            column_names.append('%s_%s_%s' % (df_name, var, stat))
    
    categorical.columns = column_names
    
    return categorical

# Function to calculate correlations with the target for a dataframe
def target_corrs(df):

    # List of correlations
    corrs = []

    # Iterate through the columns 
    for col in df.columns:
        print(col)
        # Skip the target column
        if col != 'TARGET':
            # Calculate correlation with the target
            corr = df['TARGET'].corr(df[col])

            # Append the list as a tuple
            corrs.append((col, corr))
            
    # Sort by absolute magnitude of correlations
    corrs = sorted(corrs, key = lambda x: abs(x[1]), reverse = True)
    
    return corrs

# Plots the disribution of a variable colored by value of the target
def kde_target(var_name, df):
    
    # Calculate the correlation coefficient between the new variable and the target
    corr = df['TARGET'].corr(df[var_name])
    
    # Calculate medians for repaid vs not repaid
    avg_repaid = df.ix[df['TARGET'] == 0, var_name].median()
    avg_not_repaid = df.ix[df['TARGET'] == 1, var_name].median()
    
    plt.figure(figsize = (12, 6))
    
    # Plot the distribution for target == 0 and target == 1
    sns.kdeplot(df.ix[df['TARGET'] == 0, var_name], label = 'TARGET == 0')
    sns.kdeplot(df.ix[df['TARGET'] == 1, var_name], label = 'TARGET == 1')
    
    # label the plot
    plt.xlabel(var_name); plt.ylabel('Density'); plt.title('%s Distribution' % var_name)
    plt.legend();
    
    # print out the correlation
    print('The correlation between %s and the TARGET is %0.4f' % (var_name, corr))
    # Print out average values
    print('Median value for loan that was not repaid = %0.4f' % avg_not_repaid)
    print('Median value for loan that was repaid =     %0.4f' % avg_repaid)

def get_engineered_features(df, group_var, df_name):
    categorical_agg = count_categorical(df, group_var = group_var, df_name = df_name).reset_index()
    numerical_agg = agg_numeric(df, group_var = group_var, df_name = df_name)
    return numerical_agg.merge(categorical_agg, on = group_var, how = 'inner')

def features(bureau, bureau_balance):    
    bureau_agg = get_engineered_features(bureau.drop(['SK_ID_BUREAU'], axis=1), group_var = 'SK_ID_CURR', df_name = 'bureau')    
    bureau_balance_agg = get_engineered_features(bureau_balance, group_var = 'SK_ID_BUREAU', df_name = 'bureau_balance')

    # Merge to include the SK_ID_CURR
    bureau_by_loan = bureau[['SK_ID_BUREAU', 'SK_ID_CURR']].merge(bureau_balance_agg, on = 'SK_ID_BUREAU', how = 'left')
    # Aggregate the stats for each client
    bureau_balance_by_client = agg_numeric(bureau_by_loan.drop(['SK_ID_BUREAU'], axis=1), group_var = 'SK_ID_CURR', df_name = 'client')
    
    return bureau_agg, bureau_balance_by_client

def equal_columns(col_a, col_b):
    return np.all(col_a == col_b)

from tqdm import tqdm
def duplicate_columns(df, return_dataframe = False, verbose = False, progress = True):
    '''
        a function to detect and possibly remove duplicated columns for a pandas dataframe
    '''
    # group columns by dtypes, only the columns of the same dtypes can be duplicate of each other
    groups = df.columns.to_series().groupby(df.dtypes).groups
    duplicated_columns = {}
    

        
    for dtype, col_names in groups.items():
        column_values = df[col_names]
        num_columns = len(col_names)
        
        if progress == True:
            it = tqdm(range(num_columns))
        else:
            it = range(num_columns)
        # find duplicated columns by checking pairs of columns, store first column name if duplicate exist 
        for i in it:
            column_i = column_values.iloc[:,i]
            for j in range(i + 1, num_columns):
                column_j = column_values.iloc[:,j]
                if equal_columns(column_i, column_j):
                    if verbose: 
                        print("column {} is a duplicate of column {}".format(col_names[i], col_names[j]))
                    duplicated_columns[col_names[j]] = col_names[i]
                    break
    if not return_dataframe:
        # return the column names of those duplicated exists
        return duplicated_columns
    else:
        # return a dataframe with duplicated columns dropped 
        return df.drop(labels = list(duplicated_columns.keys()), axis = 1)