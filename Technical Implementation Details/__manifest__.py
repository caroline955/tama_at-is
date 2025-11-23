{
    'name': 'Pystravel AI Forecasting',
    'version': '1.0',
    'summary': 'Dự báo doanh thu du lịch sử dụng AI (Prophet)',
    'description': """
        Module tự động phân tích dữ liệu bán hàng lịch sử
        và dự báo doanh thu trong 30 ngày tới sử dụng thuật toán Prophet.
    """,
    'category': 'Sales',
    'author': 'Group 6 - Pystravel',
    'depends': ['sale_management'],
    'data': [
        'views/forecast_views.xml',
        'data/cron_job.xml', # File định nghĩa lịch chạy tự động (xem phần 5)
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
}