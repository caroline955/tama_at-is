from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

# Cố gắng import thư viện AI, nếu chưa cài thì báo lỗi log thay vì crash
try:
    import pandas as pd
    from prophet import Prophet
except ImportError:
    _logger.warning("Thư viện 'pandas' hoặc 'prophet' chưa được cài đặt. Tính năng dự báo sẽ không hoạt động.")

class PystravelForecast(models.Model):
    _name = 'pystravel.forecast'
    _description = 'Dự báo Doanh thu Du lịch'
    _order = 'forecast_date desc'

    forecast_date = fields.Date(string='Ngày Dự báo', required=True)
    revenue_predicted = fields.Float(string='Doanh thu Dự báo (VNĐ)')
    revenue_actual = fields.Float(string='Doanh thu Thực tế (VNĐ)', help="Cập nhật khi có số liệu thực")
    confidence_lower = fields.Float(string='Ngưỡng thấp nhất')
    confidence_upper = fields.Float(string='Ngưỡng cao nhất')

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def action_run_ai_forecast(self):
        """
        Hàm này được gọi bởi Cron Job (Lên lịch tự động).
        Nó sẽ lấy dữ liệu đơn hàng, chạy AI và lưu vào bảng pystravel.forecast
        """
        _logger.info("Bắt đầu chạy dự báo AI cho Pystravel...")

        # BƯỚC 1: TRÍCH XUẤT DỮ LIỆU TỪ ODOO
        # Lấy các đơn hàng đã xác nhận (Sale Order) hoặc hoàn thành (Done)
        orders = self.search([
            ('state', 'in', ['sale', 'done']),
            ('date_order', '!=', False)
        ])

        if not orders:
            _logger.info("Không có dữ liệu đơn hàng để dự báo.")
            return

        # Chuẩn bị dữ liệu cho Pandas
        data = []
        for order in orders:
            data.append({
                'ds': order.date_order.date(),  # Prophet yêu cầu cột thời gian là 'ds'
                'y': order.amount_total         # Prophet yêu cầu cột giá trị là 'y'
            })

        # BƯỚC 2: XỬ LÝ DỮ LIỆU (PRE-PROCESSING)
        df = pd.DataFrame(data)
        # Gom nhóm doanh thu theo ngày (tổng doanh thu mỗi ngày)
        df_daily = df.groupby('ds').sum().reset_index()

        # BƯỚC 3: HUẤN LUYỆN MÔ HÌNH AI (PROPHET)
        m = Prophet(daily_seasonality=True)
        m.fit(df_daily)

        # Tạo khung thời gian tương lai (30 ngày tới)
        future = m.make_future_dataframe(periods=30)
        forecast = m.predict(future)

        # BƯỚC 4: LƯU KẾT QUẢ VÀO ODOO (WRITE-BACK)
        ForecastModel = self.env['pystravel.forecast']
        
        # Xóa dữ liệu dự báo cũ của tương lai để cập nhật mới
        today = fields.Date.today()
        ForecastModel.search([('forecast_date', '>=', today)]).unlink()

        # Lặp qua kết quả dự báo và lưu vào database
        for index, row in forecast.iterrows():
            date_val = row['ds'].date()
            
            # Chỉ lưu các ngày từ hôm nay trở đi (Dự báo tương lai)
            if date_val >= today:
                ForecastModel.create({
                    'forecast_date': date_val,
                    'revenue_predicted': row['yhat'], # Giá trị dự báo trung bình
                    'confidence_lower': row['yhat_lower'],
                    'confidence_upper': row['yhat_upper'],
                })
        
        _logger.info("Hoàn tất dự báo AI. Đã cập nhật dữ liệu cho 30 ngày tới.")