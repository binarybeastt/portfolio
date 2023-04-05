# -*- coding: utf-8 -*-
"""olympiad.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1SnphRjLrtonvMejO_9NUbuONwZYnhfl4

## Predicting Motor Insurance Claims
A notebook for Analytics Olympiad which was hosted by Machine Hack

### About the dataset
The dataset contains information on policyholders of motor insurance such as the type of vehicle,  annual mileage, household statistics, credit score, and more. 

For the competition, we are expected to obtain a target for prediction which is a binary value on whther the insurance claim occurred or not. The target column is the 'OUTCOME' in the dataset

### Objectives
In this notebook, we will explore the steps required to approach the classification problem of whether or not a claim occured, from start to finish.

The regression model is “by construction” an interpolation model.

A test set is also provided, the accuracy on the test set will determine the position of each candidate on the leaderboard. The log loss metric is to be used for measuring accuracy 

This notebook will guide us through an end-to-end process of:

1. Cleaning and Splitting Test Data
2. Exploratory Data Analysis
3. Feature Engineering
4. Model Selection
5. Advanced Feature Transformation
6. Fitting the Model
7. Hyperparameter Optimisation
8. Predicting Test Data
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
plt.rc('figure',figsize=(20,11))
sns.set_style('darkgrid')
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import OrdinalEncoder, OneHotEncoder, LabelEncoder, StandardScaler
from sklearn.neural_network import MLPClassifier, MLPRegressor

from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, AdaBoostClassifier, GradientBoostingClassifier
from sklearn.compose import ColumnTransformer

from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.svm import SVC, LinearSVC, SVR
from sklearn.naive_bayes import GaussianNB
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis
from sklearn.feature_selection import RFE
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.linear_model import LinearRegression, Ridge, LogisticRegression, Lasso

import xgboost as xgb
from xgboost import XGBClassifier
from xgboost import XGBRegressor

"""# 1. Cleaning and Splitting Test Data

### 1.1 Understanding the Dimensions
First, we'll look at basic descriptions of the data to understand what we're working with.
"""

train = pd.read_csv('train.csv')
test = pd.read_csv('test.csv')
test2 = pd.read_csv('test.csv')
train = train.drop(columns=['ID'])
train.head()

print(f"Dataset has {train.shape[0]} rows and {train.shape[1]} columns")
print(f"Duplicates: {train.duplicated().sum()}")
print(f"Total Missing Values: {train.isna().sum().sum()}")
print(f"Number of rows with missing values: {train.isna().any(axis=1).sum()}")
print('-------------------------------------')
print('For the test set')
print(f"\nDataset has {test.shape[0]} rows and {test.shape[1]} columns")
print(f"Duplicates: {test.duplicated().sum()}")
print(f"Total Missing Values: {test.isna().sum().sum()}")
print(f"Number of rows with missing values: {test.isna().any(axis=1).sum()}")

"""### 1.2 Performing Clean Up of Data
We have to be careful not to fundamentally change any values relative to others while keeping in mind that we should avoid any leakage as we have not yet split our test set.


There is not much cleanup to be done as the data is basically almost perfect
"""

train.head()

# Let's define the categorical columns and numerical columns which will be later used as features
categorical_cols = [col for col in train.columns if (train[col].nunique() < 10) and 
                    (train[col].dtype == "object") and
                    col not in ['OUTCOME']]

numerical_cols = [col for col in train.columns if (train[col].dtype in ['int64', 'float64']) and
                  col not in ['OUTCOME']]

print('Number of Numerical columns   :',len(numerical_cols))
print('Number of Categorical columns :',len(categorical_cols))

train.head()

train.info()

print(f'Dataset has {train.shape[0]} rows and {train.shape[1]} columns')
print(f'Duplicates: {train.duplicated().sum()}')
print(f'Total missing values: {train.isna().sum().sum()}')
print(f'Number of rows with missing values: {train.isna().any(axis=1).sum()}')

"""The dataset is quite imbalanced as the OUTCOME variables don't have an equal distribution in the dataset"""

train['OUTCOME'].value_counts().reset_index().plot(kind='bar')

"""## EXPLORATORY DATA ANALYSIS

### 2.1 FEATURE DISTRIBUTION
"""

def plot_col_distribution(df, n_graph_per_row):
    n_col = df.shape[1]
    column_names = list(df)
    n_graph_row = (n_col + n_graph_per_row - 1) // n_graph_per_row
    plt.figure(num = None, figsize = (6 * n_graph_per_row, 8 * n_graph_row), dpi = 80, facecolor = 'w', edgecolor = 'k')
    for i in range(n_col):
        plt.subplot(n_graph_row, n_graph_per_row, i + 1)
        column_df = df.iloc[:, i]
        if (not np.issubdtype(type(column_df.iloc[0]), np.number)):
            column_df.value_counts().plot.bar()
        else:
            column_df.hist()
        plt.ylabel('counts')
        plt.xticks(rotation = 90)
        plt.title(f'{column_names[i]} (column {i})')
    plt.tight_layout(pad = 1.0, w_pad = 1.0, h_pad = 1.0)
    plt.show()
    
plot_col_distribution(train,4)

from scipy.stats import skew
for col in numerical_cols:
    print(f'{col}: {skew(train[col])}')

"""There appears to be quite a bit of skew in some of the numerical variables.

However, we'll do our best to preserve the structure including outliers, so that we can make the most of it.

### 2.3 Checking Correlation between Variables
Understanding how the variables are related can tell us more about whether or not features are redundant. Redundant features can negatively impact the performance of the model.
"""

def plot_corr(df):
    corr = df.corr()
    plt.figure(figsize=(22,10))
    sns.heatmap(corr, cbar=True, annot=True, cmap='CMRmap')

plot_corr(train)

"""Wow! There is extremely little positive correlation among the dataset variables, some variables are also a little bit negatively correlated, this shows that there's hardly any relationship that exists between these variables.

### 2.4 Number of Categories in Each Categorical Feature
Too many categories make a feature less viable as a categorical feature.
"""

for col in categorical_cols:
    print(col, 'has', train[col].nunique(),'unique variables')

"""Fortunately, all categorical featuers have a healthy number of categories - not too many.

Some with 2 unique variables can be considered binary i.e. 2 states only.

### 2.5 Check for Missing Values

"""

print(f"Missing Values in DF: {train.isna().sum().sum()}")
print("\n")

def find_missing(df, cols:list):
    for i in cols:
        print(" - ", i, f", Missing: {df[i].isna().sum()}")
    print("\n")

print("Categorical features are:")
find_missing(train, categorical_cols)
print("Numerical features are:")
find_missing(train, numerical_cols)

print("Targets")
find_missing(train, ['OUTCOME'])

"""### 2.6 Selecting Model and Metrics
##### For the classification problem with `OUTCOME`:

This is a binary classification problem.

The chosen metric for the competition is 'log_loss' which is a measure of how close the prediction probability is close to the actual value.

### 4.3 Encoding Categorical Variables
XGBoost requires some form of encoding to function with categorical variables. 
We'll look into encoding in detail further below.

Looking at the nunique values from the EDA, and some off-screen analysis of each categorical value, there are 3 types of encoding we will perform here.

- Ordinal category: Only Education appears to have some linkage between the classes
- Binary categories: These categories have only two classes
- Nominal categories: There are multiple classes and they do not have any relationship with one another
"""

categorical_cols_ord = ['EDUCATION']
categorical_cols_bin = ['VEHICLE_YEAR', 'GENDER']
categorical_cols_nom = ['TYPE_OF_VEHICLE', 'DRIVING_EXPERIENCE', 'INCOME', 'AGE']

print('All features are accounted for:',set(categorical_cols) == set(categorical_cols_ord) | set(categorical_cols_bin) | set(categorical_cols_nom))

"""First we select the train and test columns to be encoded

Then we apply the type of encoding we have defined for each subset of data
"""

EDUCATION_ordinal = [['none', 'high school', 'university']]
ordinal_encoder_EDUCATION = OrdinalEncoder(categories=EDUCATION_ordinal)
binary_encoder = OrdinalEncoder()
oh_encoder = OneHotEncoder(handle_unknown='ignore', sparse=False)

#Take only categorical columns
train_cat = train[categorical_cols]
test_cat = test[categorical_cols]

#Encode each categorical type
#Ordinal categories
train_cat_ord = pd.DataFrame(ordinal_encoder_EDUCATION.fit_transform(train_cat[categorical_cols_ord]))
train_cat_ord.columns = train_cat[categorical_cols_ord].columns

test_cat_ord = pd.DataFrame(ordinal_encoder_EDUCATION.fit_transform(test_cat[categorical_cols_ord]))
test_cat_ord.columns = test_cat[categorical_cols_ord].columns

#Binary Categories
train_cat_bin = pd.DataFrame(binary_encoder.fit_transform(train_cat[categorical_cols_bin]))
train_cat_bin.columns = train_cat[categorical_cols_bin].columns

test_cat_bin = pd.DataFrame(binary_encoder.fit_transform(test_cat[categorical_cols_bin]))
test_cat_bin.columns = test_cat[categorical_cols_bin].columns

#Nominal Categories
train_cat_nom = pd.DataFrame(oh_encoder.fit_transform(train_cat[categorical_cols_nom]))
train_cat_nom.columns = oh_encoder.get_feature_names_out()

test_cat_nom = pd.DataFrame(oh_encoder.fit_transform(test_cat[categorical_cols_nom]))
test_cat_nom.columns = oh_encoder.get_feature_names_out()

#Rejoin the three sub df's

train_cat_enc = pd.concat([train_cat_ord, train_cat_nom, train_cat_bin], axis=1)

test_cat_enc = pd.concat([test_cat_ord, test_cat_nom, test_cat_bin], axis=1)

train_cat_enc.head()

test_cat_enc.head()

train_complete_enc = pd.concat([train[numerical_cols], train_cat_enc, train['OUTCOME']], axis=1)
test_complete_enc = pd.concat([test[numerical_cols], test_cat_enc], axis=1)

train_complete_enc.head()

test_complete_enc.head()

train_complete_enc.info()

"""
### 4.4 Dummy Variable Trap
One of the downsides of one-hot encoding is that we can fall into the Dummy Variable Trap. To avoid problems with Multicollinearity, let's look into the one-hot encoded variables.

A common practice is to drop one of the columns for each encoding, but let's evaluate how doing so reduces multicollinearity

One of the common ways to check for multicollinearity is the Variance Inflation Factor (VIF):

- VIF = 1 : Very little Multicollinearity
- VIF < 5 : Moderate Multicollinearity
- VIF > 5 : Extreme Multicollinearity (This is what we have to avoid)"""

def calc_vif(df):
    df_cols = df.columns
    vif_values = [
        variance_inflation_factor(df.values, i) for i in range(len(df_cols))
        ]
    return pd.DataFrame(zip(df_cols, vif_values),columns=['Variable','VIF'])

calc_vif(train_complete_enc.drop(['OUTCOME'], axis=1))

"""As expected, the one-hot encoded variables displayed infinite VIF, which means we have to drop one of each of the newly encoded features."""

train_complete_enc.drop(columns=['TYPE_OF_VEHICLE_HatchBack', 'DRIVING_EXPERIENCE_0-9y','INCOME_middle class', 'AGE_16-25', 'GENDER', 'INCOME_poverty', 'INCOME_upper class',], inplace=True)
test_complete_enc.drop(columns=['TYPE_OF_VEHICLE_HatchBack', 'DRIVING_EXPERIENCE_0-9y','INCOME_middle class', 'AGE_16-25', 'GENDER', 'INCOME_poverty', 'INCOME_upper class'], inplace=True)
calc_vif(train_complete_enc.drop(['OUTCOME'], axis=1))

"""# 5. Model Selection
We'll select a list of popular classifiers to compare how they fare with our selected metric.

The tests here will be brief without any deeper optimisation.
"""

# Model selection
classifiers = [

    ('Nearest Neighbors', KNeighborsClassifier(3)),
    
    ('Decision Tree', DecisionTreeClassifier(random_state=0, max_depth=5)),
    ('Random Forest', RandomForestClassifier(random_state=0, max_depth=5, n_estimators=10, max_features=1)),
    ('Neural Net', MLPClassifier(random_state=0, alpha=1, max_iter=1000)),
    ('AdaBoost', AdaBoostClassifier(random_state=0)),
    ('Naive Bayes', GaussianNB()),
    ('QDA', QuadraticDiscriminantAnalysis()),
    ('XGBoost', XGBClassifier(random_state=0, silent=True)),
    ('GBM Classifier', GradientBoostingClassifier(random_state=0))]

"""Removing our target variable..."""

y = train_complete_enc['OUTCOME']
train_complete_enc = train_complete_enc.drop(columns=['OUTCOME'])

train_complete_enc.head()

"""We're going to split dataset into train and test sets and stratify to reflect the distribution of outcomes in the target variables"""

from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(train_complete_enc, y, test_size=0.2, stratify=y)
y_train.value_counts()
y_test.value_counts()

from sklearn.metrics import log_loss
performance = []
for name, clf in classifiers:
    clf.fit(X_train, y_train)
    y_pred = clf.predict_proba(X_test)
    perf_tuple = (name, log_loss(y_test, y_pred))
    print(perf_tuple)
    performance.append(perf_tuple)

"""From the above, we can see clearly that all 3 of the GBM, XGBoost, RandomForest and AdaBoost Classifiers performed similarly, these results are enough for us to decide to proceed with a GBM variant.

Although RandomForest performed marginally better here, we'll use XGBoost since it's the more advanced, more tuneable algorithm.

Thus, we'll focus on performing more specific transformations to aid XGBoost.

# 6. Advanced Feature Transformations
In order to support the selected model, we should consider how to transform the dataset such that they can improve the performance of the model.
"""

from sklearn.metrics import log_loss
xgb = XGBClassifier()
xgb.fit(X_train, y_train)
y_pred = xgb.predict_proba(X_test)
print(log_loss(y_test, y_pred))

"""<span style="color:red">After getting this score, I made prediction on the validation set and uploaded my submissions file to the leaderboard. My model was severely overfitting as I had a score of around 1.9 on the validation set and my position on the leaderboard was wayyyyy down.</span>

### 6.1 Feature Extraction
Sometimes, we can perform Feature Extraction but in our dataset, most features are straightforward and need no further extraction

### 6.2 Numerical only for XGBoost
XGBoost works with numerical data only, and fortunately our base dataframe is already encoded into numerical features.

### 6.3 Feature Scaling
Decision Tree based classifiers, which XGBoost is based on, are insensitive to scaling.

### 6.4 Feature Selection
We can reduce dimensionality but XGBoost naturally handles this usually. 

Nevertheless, let's experiment with two methods of dimensionality reduction, namely Recursive Feature Elimination (RFE) and our old friend Variance Inflation Factor (VIF)

##### 6.4.1 Recursive Feature Elimination
Let's assume a simple model (to reduce run time)[](http://), such as a Decision Tree Classifier, to help us decide which features to eliminate.
"""

from sklearn.pipeline import Pipeline

rfe = RFE(
estimator=DecisionTreeClassifier(),
n_features_to_select=10
)

pipe = Pipeline([('rfe',rfe)])
transformed_df_rfe = pipe.fit_transform(X_train, y_train)
support = pipe.named_steps['rfe'].support_
drop_cols_rfe = list(X_train.columns[support])

"""##### 6.4.2 Variance Inflation Factor Selection
Just as we have performed after the One-hot Encoding, we can perform the same selection, by removing features with a VIF greater than 5.
"""

vif_df = calc_vif(X_train)
drop_cols_vif = vif_df.loc[vif_df['VIF']>5]['Variable'].values
transformed_df_rfe_vif = X_train.drop(drop_cols_vif,axis=1)
display(calc_vif(transformed_df_rfe_vif))

"""We print out list of columns that the RFE and VIF has suggested to drop"""

print('RFE - Columns to be dropped:', list(drop_cols_rfe))
print('VIF - Columns to be dropped:', list(drop_cols_vif))

"""And we remove columns that are common to both lists"""

transformed_train = train_complete_enc.drop(columns=['CREDIT_SCORE', 'ANNUAL_MILEAGE'])
X_train, X_test, y_train, y_test = train_test_split(transformed_train, y, test_size=0.2, stratify=y)

xgb = XGBClassifier(silent=True)
xgb.fit(X_train, y_train)
y_pred = xgb.predict_proba(X_test)
print(log_loss(y_test, y_pred))

"""We can see that the feature selection had no change in our log_loss score

<span style="color:red">I made prediction again and submitted and my model was still overfitting</span>

### 6.5 Log Transformation

Here we transform our skewed features
"""

high_skew_features = []

for col in numerical_cols:
    skewness = skew(train_complete_enc[col])
    asterisk = '* ' if skewness > 1 else ''
    print(f"{asterisk}{col} : {skewness}")
    if skewness > 1:
        high_skew_features.append(col)

transformed_df_log = train_complete_enc.copy()
transformed_test_log = test_complete_enc.copy()
for col in high_skew_features:
    transformed_df_log['log_'+col] = np.log(1 + transformed_df_log[col])
    transformed_test_log['log_'+col] = np.log(1 + transformed_test_log[col])

transformed_df_log.drop(high_skew_features, axis=1)
transformed_test_log.drop(high_skew_features, axis=1)
transformed_df_log.head()

"""# 7. Fitting the Model

Before fitting the model finally, I'm going to try to optimize the model by tuning hyperparameters
"""

import optuna
import xgboost as xgb
from sklearn.metrics import log_loss
def objective(trial,data=transformed_df_log,target=y):
    
    train_x, test_x, train_y, test_y = train_test_split(data, target, test_size=0.15,random_state=42)
    param = {
        'tree_method':'auto',
        'silent' : True,
        'lambda': trial.suggest_loguniform('lambda', 1e-3, 10.0),
        'alpha': trial.suggest_loguniform('alpha', 1e-3, 10.0),
        'colsample_bytree': trial.suggest_categorical('colsample_bytree', [0.3,0.4,0.5,0.6,0.7,0.8,0.9, 1.0]),
        'subsample': trial.suggest_categorical('subsample', [0.4,0.5,0.6,0.7,0.8,1.0]),
        'learning_rate': trial.suggest_categorical('learning_rate', [0.008,0.01,0.012,0.014,0.016,0.018, 0.02]),
        'n_estimators': 10000,
        'max_depth': trial.suggest_categorical('max_depth', [5,7,9,11,13,15,17]),
        'random_state': trial.suggest_categorical('random_state', [2020]),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 300),
    }
    model = xgb.XGBClassifier(**param)  
    
    model.fit(train_x,train_y,eval_set=[(test_x,test_y)],early_stopping_rounds=100,verbose=False)
    
    preds = model.predict(test_x)
    
    accuracy = log_loss(test_y, preds)
    
    return accuracy

study = optuna.create_study(direction='minimize')
study.optimize(objective, n_trials=30)
print('Number of finished trials:', len(study.trials))
print('Best trial:', study.best_trial.params)

#plot_optimization_histor: shows the scores from all trials as well as the best score so far at each point.
optuna.visualization.plot_optimization_history(study)

#plot_parallel_coordinate: interactively visualizes the hyperparameters and scores
optuna.visualization.plot_parallel_coordinate(study)

#Visualize parameter importances.
optuna.visualization.plot_param_importances(study)

"""Finally, we get a list of our optimal hyperparameters and then train the final model with it"""

Best_trial = study.best_trial.params
Best_trial["n_estimators"], Best_trial["tree_method"] = 10000, 'auto'
Best_trial

X_train, X_test, y_train, y_test = train_test_split(transformed_df_log, y, test_size=0.2, stratify=y)
model = xgb.XGBClassifier(**Best_trial)
model.fit(X_train, y_train)
y_pred = model.predict_proba(X_test)
print(log_loss(y_test, y_pred))

sub_file = pd.DataFrame(model.predict_proba(transformed_test_log))

def pred(value):
    if value>= 0.5:
        return 1
    else:
        return 0

sub_file['OUTCOME'] = sub_file[0].apply(lambda x: pred(x))
sub_file.drop(columns=[0, 1], inplace=True)
sub_file.to_csv('baseline3.csv')

"""<span style="color:red">I was able to get rid of overfitting eventually and scored 0.69 on the validaton set, at this time of submission, I was 65th on the leaderboard, the first has a score of 0.68</span>
 
 
 I will also keep trying to make my score better, hopefully before the deadline

Great! That wraps up our prediction on the Insurance claim!

# Conclusion
Hope you've enjoyed this journey with me.

There are so many differing methodologies out there, and this one is mine.

There's probably several areas in this notebook that could have been improved upon but I wish I had more time to dive deeper into.

If you have a better suggestion on how one could improve the model, feel free to comment! I'm always open to constructive feedback on improving my work.

-----

### About the Author

Hi, I'm Bola, a passionate data scientist, understanding the world through data and models.

I may be available for Data Science work and more, please feel free to leave me an email here (no spam please!): ibolarinwa606@gmail.com

Let's chat more if we're a good fit. Don't overfit! ;)

Always learning.
"""