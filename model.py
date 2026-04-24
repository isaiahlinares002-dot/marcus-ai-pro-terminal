from sklearn.ensemble import RandomForestClassifier

def train_model(X, y):
    model = RandomForestClassifier(n_estimators=150, max_depth=6)
    model.fit(X, y)
    return model