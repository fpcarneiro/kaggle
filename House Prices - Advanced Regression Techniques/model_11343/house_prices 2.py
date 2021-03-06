import preprocessing as pp
import ensemble as em
import feature_selection as fs
import cv_lab as cvl
import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler
from sklearn.kernel_ridge import KernelRidge
from xgboost import XGBRegressor
import lightgbm as lgb
from sklearn.svm import SVR, LinearSVR
from sklearn.linear_model import ElasticNet, Lasso, BayesianRidge, Ridge, SGDRegressor, LassoLars
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, ExtraTreesRegressor
from sklearn.model_selection import train_test_split

import warnings
def ignore_warn(*args, **kwargs):
    pass
warnings.warn = ignore_warn #ignore annoying warning (from sklearn and seaborn)

train_X, train_y, test_X, ids = pp.get_processed_datasets()

features_variance = fs.list_features_low_variance(train_X, train_y)

train_X = train_X[features_variance]
test_X = test_X[features_variance]

importances = fs.get_feature_importance(Lasso(alpha=0.000507), train_X, train_y)
fs.plot_features_importances(importances, show_importance_zero = False)

features_select_from_model, pipe_select_from_model = fs.remove_features_from_model(estimator = Lasso(alpha = 0.000507), 
                                                          scaler = RobustScaler(), X = train_X, y = train_y)
train_X_reduced = pipe_select_from_model.transform(train_X)
test_X_reduced = pipe_select_from_model.transform(test_X)

# split into a training and testing set
X_train, X_test, y_train, y_test = train_test_split(train_X_reduced, train_y, 
                                                    test_size=0.20, random_state=42)

#########################################################################################################

model_lasso = Lasso(alpha = 0.000507, random_state = 1)
model_ridge = Ridge(alpha=10.0)
model_svr = SVR(C = 15, epsilon = 0.009, gamma = 0.0004, kernel = 'rbf')
model_ENet = ElasticNet(alpha=0.0005, l1_ratio=.9, random_state=3, max_iter = 10000)
model_KRR = KernelRidge(alpha=0.5, kernel='polynomial', degree=2, coef0=2.5)
model_byr = BayesianRidge()
model_rforest = RandomForestRegressor(n_estimators = 210)

model_lsvr = LinearSVR()
model_sgd = SGDRegressor()
model_extra = ExtraTreesRegressor()

model_xgb = XGBRegressor(colsample_bytree=0.4603, gamma=0.0468, 
                             learning_rate=0.05, max_depth=4, 
                             min_child_weight=1.7817, n_estimators=3000,
                             reg_alpha=0.4640, reg_lambda=0.88,
                             subsample=0.5213, silent=1,
                             random_state =7, nthread = -1)

model_GBoost = GradientBoostingRegressor(n_estimators=3000, learning_rate=0.05,
                                   max_depth=4, max_features='sqrt',
                                   min_samples_leaf=15, min_samples_split=10, 
                                   loss='huber', random_state =5)

model_lgb = lgb.LGBMRegressor(objective='regression',num_leaves=5,
                              learning_rate=0.05, n_estimators=720,
                              max_bin = 55, bagging_fraction = 0.8,
                              bagging_freq = 5, feature_fraction = 0.2319,
                              feature_fraction_seed=9, bagging_seed=9,
                              min_data_in_leaf =6, min_sum_hessian_in_leaf = 11)

model_lasso_lars = LassoLars(alpha = 0.000507)

#Linear Models
models = []
models.append(("lasso", model_lasso))
models.append(("ridge", model_ridge))
models.append(("svr", model_svr))
models.append(("ENet", model_ENet))
models.append(("KRR", model_KRR))
models.append(("byr", model_byr))
models.append(("rforest", model_rforest))
models.append(("xgb", model_xgb))
models.append(("GBoost", model_GBoost))
models.append(("lgb", model_lgb))
models.append(("lasso_lars", model_lasso_lars))
models.append(("lsvr", model_lsvr))
#models.append(("sgd", model_sgd))
#models.append(("extra", model_extra))
models.append(("average", em.AveragingModels(models = [model_ridge, model_byr, model_xgb])))

######## cross validation #####################################################
def cross_validation_models(models_set, X_train_set, y_train_set):
    scores = []
    names = []
    for name, model in models_set:
        names.append(name)
        scores.append(np.sqrt(pp.score_model(model, X_train_set, y_train_set)).mean())
    tab = pd.DataFrame({ "Model" : names, "Score" : scores })
    tab = tab.sort_values(by=['Score'], ascending = True)
    return(tab)

######## test models ##########################################################
def train_test_models(models_set, X_train_set, y_train_set, X_test_set, y_test_set):
    scores = []
    names = []
    for name, model in models_set:
        model.fit(X_train_set, y_train_set)
        predicted_prices = model.predict(X_test_set)
        score = cvl.score_sq(y_test_set, predicted_prices)
        names.append(name)
        scores.append(score)
    tab = pd.DataFrame({ "Model" : names, "Score" : scores })
    tab = tab.sort_values(by=['Score'], ascending = True)
    return(tab)

cross_validation_table = cross_validation_models(models, train_X_reduced, train_y)
print(cross_validation_table)

test_table = train_test_models(models, X_train, y_train, X_test, y_test)
print(test_table)

def train_submit(model, X_train_set, y_train_set, test_X_to_submit, file_name = 'submission.csv'):
    model.fit(X_train_set, y_train_set)
    predicted = np.expm1(model.predict(test_X_to_submit))
    print(predicted)
    submission = pd.DataFrame({'Id': ids, 'SalePrice': predicted})
    submission.to_csv(file_name, index=False)
    
train_submit(em.AveragingModels(models = [model_svr, model_byr, model_xgb]), 
                                                                      train_X_reduced, train_y, test_X_reduced,
                                                                      'submission_avg_1.csv')
    
    
    
# Best one so far: model_svr, model_KRR, model_xgb
# Try this combination: model_svr, model_KRR, averaged_models_tree
averaged_models = em.AveragingModels(models = [model_svr, model_KRR, model_xgb])

score_avg = np.sqrt(pp.score_model(averaged_models, train_X_reduced, train_y))
print(" Averaged base models score: {:.6f} ({:.6f})\n".format(score_avg.mean(), score_avg.std()))



stacked_averaged_models = em.StackingAveragedModels(base_models = [model_KRR, model_xgb],
                                                 meta_model = model_svr)

score_stacked_averaged = np.sqrt(pp.score_model(stacked_averaged_models, train_X_reduced, train_y))
print(" Stacked Averaged base models score: {:.6f} ({:.6f})\n".format(score_stacked_averaged.mean(), 
      score_stacked_averaged.std()))

stacked_averaged_models.fit(train_X_reduced, train_y)
predicted_prices_stacked_averaged = np.expm1(stacked_averaged_models.predict(test_X_reduced))
print(predicted_prices_stacked_averaged)

model_xgb.fit(train_X_reduced, train_y)
predicted_prices_xgboost = np.expm1(model_xgb.predict(test_X_reduced))
print(predicted_prices_xgboost)

model_lgb.fit(train_X_reduced, train_y)
predicted_prices_lgb = np.expm1(model_lgb.predict(test_X_reduced))
print(predicted_prices_lgb)

predicted_prices = predicted_prices_stacked_averaged*0.7 + predicted_prices_xgboost*0.2 + predicted_prices_lgb*0.1

my_submission = pd.DataFrame({'Id': ids, 'SalePrice': predicted_prices})
my_submission.to_csv('submission_ensemble.csv', index=False)




averaged_models_tree = em.AveragingModels(models = [model_lgb, model_GBoost])

score_avg_tree = np.sqrt(pp.score_model(averaged_models_tree, train_X_reduced, train_y))
print(" Averaged base models score: {:.6f} ({:.6f})\n".format(score_avg_tree.mean(), score_avg_tree.std()))

averaged_models_linear = em.AveragingModels(models = [model_svr, model_KRR])

score_avg_linear = np.sqrt(pp.score_model(averaged_models_linear, train_X_reduced, train_y))
print(" Averaged base models score: {:.6f} ({:.6f})\n".format(score_avg_linear.mean(), score_avg_linear.std()))


averaged = em.AveragingModels(models = [averaged_models_tree, averaged_models_linear])

score_avg_all = np.sqrt(pp.score_model(averaged, train_X_reduced, train_y))
print(" Averaged base models score: {:.6f} ({:.6f})\n".format(score_avg_all.mean(), score_avg_all.std()))

averaged.fit(train_X_reduced, train_y)
predicted_prices_averaged_all = np.expm1(averaged.predict(test_X_reduced))
print(predicted_prices_averaged_all)
my_submission = pd.DataFrame({'Id': ids, 'SalePrice': predicted_prices_averaged_all})
my_submission.to_csv('submission_avg.csv', index=False)