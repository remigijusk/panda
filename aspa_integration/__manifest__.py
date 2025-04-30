# Copyright (C) 2025 devtouch!, UAB
# https://www.devtouch.lt

{
    "name": "ASPA integration",
    "version": "18.0.0.2.4",
    "license": "Other proprietary",
    "author": "UAB 'Devtouch!'",
    "website": "https://www.devtouch.lt",
    "contributors": [
        "Mikas Gudzinevičius <mikas@devtouch.lt>",
    ],
    "category": "All Categories",
    "depends": [
        "point_of_sale"
    ],
    "data": [
        "views/res_config_views.xml",
        "views/product_views.xml",
        "views/pos_config_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "aspa_integration/static/src/js/aspa_api.js",
            "aspa_integration/static/src/js/payment_screen_extension.js",
            "aspa_integration/static/src/js/cash_move_popup.js",
            "aspa_integration/static/src/js/pos_store.js",
            "aspa_integration/static/src/js/closing_popup.js",
            "aspa_integration/static/src/js/opening_control_popup.js",
            "aspa_integration/static/src/xml/navbar.xml",
        ],
    },
    "installable": True,
    "application": True,
    "images": [
        "static/description/icon.png",
    ],
}
