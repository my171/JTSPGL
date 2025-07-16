import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
def predict_future_sales(sales_data, months, target_month):
    """
    Predict sales for a target month using ARIMA model
    
    Args:
        months: List of months in format "YYYY-MM" (e.g., ["2023-01", "2023-02"])
        sales_data: List of sales numbers corresponding to the months
        target_month: Target month to predict in same "YYYY-MM" format
        
    Returns:
        Predicted sales for the target month
    """
    # Convert input to pandas Series with datetime index
    dates = pd.to_datetime(months, format='%Y-%m')
    ts = pd.Series(sales_data, index=dates)
    
    # Fit ARIMA model - parameters can be adjusted based on your data
    # (p,d,q) = (autoregressive, differencing, moving average)
    model = ARIMA(ts, order=(1, 1, 1))  # Start with simple (1,1,1) model
    model_fit = model.fit()
    
    # Calculate how many steps ahead we need to forecast
    last_date = ts.index[-1]
    target_date = pd.to_datetime(target_month, format='%Y-%m')
    steps_ahead = (target_date.year - last_date.year) * 12 + (target_date.month - last_date.month)
    
    if steps_ahead <= 0:
        raise ValueError("Target month must be after the last observed month")
    
    # Make prediction
    forecast = model_fit.forecast(steps=steps_ahead)
    predicted_sales = forecast.iloc[-1]  # Get the prediction for our target month
    
    return predicted_sales

# Example usage
if __name__ == "__main__":
    # Sample data - replace with your actual data
    months = ["2023-11", "2023-12", "2024-01", "2024-02", "2024-03", "2024-04"]
    sales = [105, 110, 114, 120, 125, 131]  # Sample sales data
    target_month = "2024-06"  # Want to predict sales for August 2023
    
    try:
        prediction = predict_future_sales(sales, months, target_month)
        print(f"Predicted sales for {target_month}: {prediction:.2f}")
    except Exception as e:
        print(f"Prediction failed: {str(e)}")