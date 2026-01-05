-- ============================================
-- 订单表数据库脚本（最终修复版）
-- 创建订单表并插入30条虚假数据用于测试
-- 修复了 [ERR] 1064 和 [ERR] 1136 问题
-- ============================================

-- 创建订单表
CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(32) PRIMARY KEY COMMENT '订单唯一标识符',
    user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
    user_name VARCHAR(100) NOT NULL COMMENT '用户姓名',
    user_phone VARCHAR(20) NOT NULL COMMENT '用户手机号',
    user_address TEXT NOT NULL COMMENT '收货地址',
    
    -- 订单基本信息
    order_status ENUM('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded') NOT NULL DEFAULT 'pending' COMMENT '订单状态',
    order_type ENUM('normal', 'rush', 'bulk') NOT NULL DEFAULT 'normal' COMMENT '订单类型',
    payment_method ENUM('wechat', 'alipay', 'bank_card', 'credit_card', 'cash_on_delivery') NOT NULL COMMENT '支付方式',
    payment_status ENUM('unpaid', 'paid', 'refunded', 'failed') NOT NULL DEFAULT 'unpaid' COMMENT '支付状态',
    
    -- 商品信息
    product_name VARCHAR(200) NOT NULL COMMENT '商品名称',
    product_sku VARCHAR(100) NOT NULL COMMENT '商品SKU',
    product_category VARCHAR(50) NOT NULL COMMENT '商品分类',
    product_description TEXT COMMENT '商品描述',
    quantity INT NOT NULL DEFAULT 1 COMMENT '购买数量',          -- ✅ 修正：NOT NULL DEFAULT 1
    unit_price DECIMAL(10, 2) NOT NULL COMMENT '单价',
    
    -- 价格信息（共7个字段）
    subtotal DECIMAL(10, 2) NOT NULL COMMENT '小计',
    shipping_fee DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT '运费',
    discount_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT '优惠金额',
    tax_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT '税费',
    total_amount DECIMAL(10, 2) NOT NULL COMMENT '订单总金额',
    
    -- 时间信息
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    confirmed_at DATETIME NULL COMMENT '确认时间',
    shipped_at DATETIME NULL COMMENT '发货时间',
    delivered_at DATETIME NULL COMMENT '送达时间',
    
    -- 物流信息
    tracking_number VARCHAR(50) NULL COMMENT '快递单号',
    logistics_company VARCHAR(50) NULL COMMENT '快递公司',
    
    -- 备注信息
    customer_notes TEXT NULL COMMENT '客户备注',
    admin_notes TEXT NULL COMMENT '管理员备注',
    reason_for_cancellation TEXT NULL COMMENT '取消原因',
    
    -- 索引
    INDEX idx_user_id (user_id),
    INDEX idx_order_status (order_status),
    INDEX idx_created_at (created_at),
    INDEX idx_payment_status (payment_status),
    INDEX idx_product_sku (product_sku)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单表';

-- ============================================
-- 插入30条虚假订单数据（每行严格28个值）
-- 注意：reason_for_cancellation 未插入（保持 NULL）
-- ============================================

INSERT INTO orders (
    order_id, user_id, user_name, user_phone, user_address,
    order_status, order_type, payment_method, payment_status,
    product_name, product_sku, product_category, product_description, quantity, unit_price,
    subtotal, shipping_fee, discount_amount, tax_amount, total_amount,
    created_at, confirmed_at, shipped_at, delivered_at,
    tracking_number, logistics_company, customer_notes, admin_notes
) VALUES

-- 订单1: 已完成的订单
('ORD2025010400001', 'user001', '张三', '13800138001', '北京市朝阳区建国路88号SOHO现代城A座1201室',
 'delivered', 'normal', 'wechat', 'paid',
 'iPhone 15 Pro 256GB', 'IP15P256G', '手机', '苹果最新旗舰手机，256GB存储，深空黑色',
 1, 8999.00, 8999.00, 0.00, 0.00, 899.00, 9898.00,
 '2025-01-01 10:30:00', '2025-01-01 10:35:00', '2025-01-02 14:20:00', '2025-01-03 09:15:00',
 'SF1234567890', '顺丰速运', '请安排工作时送达', '已确认订单，立即发货'),

-- 订单2: 正在配送中的订单
('ORD2025010400002', 'user002', '李四', '13800138002', '上海市浦东新区陆家嘴环路1000号恒生银行大厦15楼',
 'shipped', 'rush', 'alipay', 'paid',
 'MacBook Air M3 13英寸', 'MBA13M3', '笔记本电脑', '苹果M3芯片MacBook Air，13英寸，轻薄便携',
 1, 9999.00, 9999.00, 15.00, 0.00, 999.00, 11013.00,
 '2025-01-02 14:20:00', '2025-01-02 14:25:00', '2025-01-03 16:30:00', NULL,
 'JD9876543210', '京东物流', '急需使用，请加急配送', '加急订单，已优先处理'),

-- 订单3: 已取消的订单
('ORD2025010400003', 'user003', '王五', '13800138003', '广州市天河区珠江新城花城大道85号高德置地春广场',
 'cancelled', 'normal', 'bank_card', 'refunded',
 'iPad Pro 12.9英寸', 'IPAD129', '平板电脑', '苹果iPad Pro 12.9英寸，M2芯片，支持Apple Pencil',
 1, 7999.00, 7999.00, 0.00, 0.00, 800.00, 8799.00,
 '2025-01-01 09:15:00', '2025-01-01 09:20:00', NULL, NULL,
 NULL, NULL, '暂时不需要了', '客户主动取消订单，已退款'),

-- 订单4: 待确认的订单
('ORD2025010400004', 'user004', '赵六', '13800138004', '深圳市南山区科技园南区深南大道9988号',
 'pending', 'normal', 'credit_card', 'unpaid',
 'AirPods Pro 2', 'APP2', '耳机', '苹果AirPods Pro第二代，主动降噪无线耳机',
 1, 1899.00, 1899.00, 0.00, 0.00, 190.00, 2089.00,
 '2025-01-03 11:45:00', NULL, NULL, NULL,
 NULL, NULL, '请尽快确认', NULL),

-- 订单5: 处理中的订单
('ORD2025010400005', 'user005', '孙七', '13800138005', '杭州市西湖区文三路259号昌地火炬大厦',
 'processing', 'bulk', 'alipay', 'paid',
 'iPhone 15 128GB x10台', 'IP15128GBx10', '手机', '批量采购iPhone 15，128GB存储，10台装',
 10, 5999.00, 59990.00, 0.00, 0.00, 5999.00, 65989.00,
 '2025-01-02 16:30:00', '2025-01-02 16:35:00', NULL, NULL,
 NULL, NULL, '公司采购，需要发票', '企业客户，批量订单'),

-- 订单6: 已发货的订单
('ORD2025010400006', 'user006', '周八', '13800138006', '成都市锦江区天府广场西南侧锦江宾馆',
 'shipped', 'normal', 'wechat', 'paid',
 'Apple Watch Series 9', 'AWS9', '智能手表', '苹果Apple Watch Series 9，45mm GPS+蜂窝网络',
 1, 2999.00, 2999.00, 0.00, 0.00, 300.00, 3299.00,
 '2025-01-03 08:20:00', '2025-01-03 08:25:00', '2025-01-03 18:45:00', NULL,
 'YT1234567890', '圆通速递', '工作日配送', '已发货，预计明日到达'),

-- 订单7: 已完成的订单
('ORD2025010400007', 'user007', '吴九', '13800138007', '武汉市洪山区光谷大道77号光谷金融港',
 'delivered', 'normal', 'bank_card', 'paid',
 'iPad Air 10.9英寸', 'IADA109', '平板电脑', '苹果iPad Air，M1芯片，10.9英寸显示屏',
 1, 4999.00, 4999.00, 0.00, 0.00, 500.00, 5499.00,
 '2024-12-28 14:10:00', '2024-12-28 14:15:00', '2024-12-29 10:30:00', '2024-12-30 16:20:00',
 'ZT9876543210', '中通快递', '学生使用', '学生订单，已确认收货'),

-- 订单8: 已确认的订单
('ORD2025010400008', 'user008', '郑十', '13800138008', '西安市雁塔区小寨东路126号百隆广场',
 'confirmed', 'normal', 'cash_on_delivery', 'unpaid',
 'Mac Studio M3', 'MSM3', '台式电脑', '苹果Mac Studio，M3芯片，专业级台式机',
 1, 14999.00, 14999.00, 50.00, 0.00, 1500.00, 16549.00,
 '2025-01-03 15:20:00', '2025-01-03 15:25:00', NULL, NULL,
 NULL, NULL, '货到付款，请准备好现金', '货到付款订单'),

-- 订单9: 处理中的订单
('ORD2025010400009', 'user009', '陈一', '13800138009', '南京市鼓楼区中山路1号南京新街口百货商店',
 'processing', 'rush', 'alipay', 'paid',
 'iPhone 15 Plus 512GB', 'IP15P512G', '手机', '苹果iPhone 15 Plus，512GB存储，粉色',
 1, 9999.00, 9999.00, 0.00, 0.00, 1000.00, 10999.00,
 '2025-01-03 12:10:00', '2025-01-03 12:15:00', NULL, NULL,
 NULL, NULL, '女朋友的生日礼物，请加急', '生日礼物订单，优先处理'),

-- 订单10: 已完成的订单
('ORD2025010400010', 'user010', '李二', '13800138010', '天津市和平区南京路226号世纪商厦',
 'delivered', 'normal', 'wechat', 'paid',
 'Apple Vision Pro', 'AVP', 'AR/VR设备', '苹果Vision Pro，混合现实头显设备',
 1, 29999.00, 29999.00, 0.00, 0.00, 3000.00, 32999.00,
 '2024-12-25 09:30:00', '2024-12-25 09:35:00', '2024-12-26 14:20:00', '2024-12-28 11:30:00',
 'SF1122334455', '顺丰速运', '开发测试使用', '企业采购，设备已验收'),

-- 订单11: 待确认的订单
('ORD2025010400011', 'user011', '王三', '13800138011', '重庆市渝中区解放碑步行街8号时代广场',
 'pending', 'normal', 'credit_card', 'unpaid',
 'MacBook Pro 14英寸 M3 Pro', 'MBP14M3P', '笔记本电脑', '苹果MacBook Pro 14英寸，M3 Pro芯片',
 1, 16999.00, 16999.00, 0.00, 0.00, 1700.00, 18699.00,
 '2025-01-03 17:45:00', NULL, NULL, NULL,
 NULL, NULL, '需要确认库存情况', '高价值商品，需确认库存'),

-- 订单12: 已发货的订单
('ORD2025010400012', 'user012', '张四', '13800138012', '青岛市市南区香港中路10号颐和国际',
 'shipped', 'normal', 'bank_card', 'paid',
 'iPad mini 8.3英寸', 'IPM83', '平板电脑', '苹果iPad mini，A15芯片，8.3英寸',
 1, 3999.00, 3999.00, 0.00, 0.00, 400.00, 4399.00,
 '2025-01-02 19:30:00', '2025-01-02 19:35:00', '2025-01-03 14:20:00', NULL,
 'HT5566778899', '汇通快递', '家用平板', '已发货，3天内到达'),

-- 订单13: 已取消的订单
('ORD2025010400013', 'user013', '刘五', '13800138013', '大连市中山区人民路55号大连商品交易所',
 'cancelled', 'normal', 'wechat', 'refunded',
 'iPhone 14 Pro Max 1TB', 'IP14PM1TB', '手机', '苹果iPhone 14 Pro Max，1TB存储，深紫色',
 1, 10999.00, 10999.00, 0.00, 0.00, 1100.00, 12099.00,
 '2024-12-30 13:20:00', '2024-12-30 13:25:00', NULL, NULL,
 NULL, NULL, '重复下单了', '客户重复下单，已取消并退款'),

-- 订单14: 已完成的订单
('ORD2025010400014', 'user014', '赵六', '13800138014', '长沙市天心区五一大道168号新世纪大厦',
 'delivered', 'normal', 'alipay', 'paid',
 'AirPods 3代', 'AP3', '耳机', '苹果AirPods第三代，无线耳机',
 1, 1399.00, 1399.00, 0.00, 0.00, 140.00, 1539.00,
 '2025-01-01 16:45:00', '2025-01-01 16:50:00', '2025-01-02 11:30:00', '2025-01-03 14:15:00',
 'ST9988776655', '申通快递', '通勤使用', '学生优惠，已确认收货'),

-- 订单15: 已确认的订单
('ORD2025010400015', 'user015', '孙七', '13800138015', '哈尔滨市南岗区红军街15号亚太大厦',
 'confirmed', 'normal', 'cash_on_delivery', 'unpaid',
 'Apple TV 4K', 'ATV4K', '流媒体设备', '苹果Apple TV 4K第三代，64GB存储',
 1, 1399.00, 1399.00, 0.00, 0.00, 140.00, 1539.00,
 '2025-01-03 10:15:00', '2025-01-03 10:20:00', NULL, NULL,
 NULL, NULL, '客厅娱乐设备', '货到付款商品'),

-- 订单16: 处理中的订单
('ORD2025010400016', 'user016', '周八', '13800138016', '石家庄市长安区中山东路303号世贸广场',
 'processing', 'bulk', 'alipay', 'paid',
 'iPad Pro 11英寸 x5台', 'IPAD11x5', '平板电脑', '苹果iPad Pro 11英寸，M2芯片，批量采购5台',
 5, 6999.00, 34995.00, 0.00, 0.00, 3500.00, 38495.00,
 '2025-01-02 11:30:00', '2025-01-02 11:35:00', NULL, NULL,
 NULL, NULL, '学校采购教育设备', '教育机构批量订单'),

-- 订单17: 已发货的订单
('ORD2025010400017', 'user017', '吴九', '13800138017', '太原市迎泽区迎泽大街218号山西大厦',
 'shipped', 'rush', 'wechat', 'paid',
 'MacBook Air M2 13英寸', 'MBA13M2', '笔记本电脑', '苹果MacBook Air，M2芯片，13英寸',
 1, 8999.00, 8999.00, 15.00, 0.00, 900.00, 9914.00,
 '2025-01-03 09:20:00', '2025-01-03 09:25:00', '2025-01-03 20:30:00', NULL,
 'YD7788990011', '韵达快递', '工作笔记本', '加急发货，次日达'),

-- 订单18: 已完成的订单
('ORD2025010400018', 'user018', '郑十', '13800138018', '合肥市庐阳区长江中路369号合肥百货大楼',
 'delivered', 'normal', 'bank_card', 'paid',
 'iPhone 15 256GB', 'IP15256G', '手机', '苹果iPhone 15，256GB存储，蓝色',
 1, 6999.00, 6999.00, 0.00, 0.00, 700.00, 7699.00,
 '2024-12-29 14:50:00', '2024-12-29 14:55:00', '2024-12-30 16:40:00', '2025-01-01 10:25:00',
 'SF5544332211', '顺丰速运', '新年礼物', '节日订单，已确认收货'),

-- 订单19: 待确认的订单
('ORD2025010400019', 'user019', '陈一', '13800138019', '福州市鼓楼区五四路128号恒力城',
 'pending', 'normal', 'credit_card', 'unpaid',
 'iPad Air 10.9英寸 蜂窝版', 'IADA109C', '平板电脑', '苹果iPad Air，蜂窝网络版，10.9英寸',
 1, 5999.00, 5999.00, 0.00, 0.00, 600.00, 6599.00,
 '2025-01-03 13:25:00', NULL, NULL, NULL,
 NULL, NULL, '需要蜂窝版', '需要确认蜂窝版库存'),

-- 订单20: 已确认的订单
('ORD2025010400020', 'user020', '李二', '13800138020', '南昌市东湖区八一大道365号江西艺术剧院',
 'confirmed', 'normal', 'cash_on_delivery', 'unpaid',
 'Apple Watch SE', 'AWSE', '智能手表', '苹果Apple Watch SE，第二代，GPS版',
 1, 1999.00, 1999.00, 0.00, 0.00, 200.00, 2199.00,
 '2025-01-03 14:40:00', '2025-01-03 14:45:00', NULL, NULL,
 NULL, NULL, '运动手表', '货到付款'),

-- 订单21: 处理中的订单
('ORD2025010400021', 'user021', '王三', '13800138021', '昆明市五华区东风西路123号昆明百货大楼',
 'processing', 'rush', 'alipay', 'paid',
 'Mac Studio M2', 'MSM2', '台式电脑', '苹果Mac Studio，M2芯片，专业工作站',
 1, 12999.00, 12999.00, 0.00, 0.00, 1300.00, 14299.00,
 '2025-01-03 08:55:00', '2025-01-03 09:00:00', NULL, NULL,
 NULL, NULL, '设计工作使用', '设计师专用设备'),

-- 订单22: 已发货的订单
('ORD2025010400022', 'user022', '张四', '13800138022', '兰州市城关区东岗东路398号兰州饭店',
 'shipped', 'normal', 'wechat', 'paid',
 'iPad mini 8.3英寸 蜂窝版', 'IPM83C', '平板电脑', '苹果iPad mini，蜂窝网络版，8.3英寸',
 1, 4999.00, 4999.00, 0.00, 0.00, 500.00, 5499.00,
 '2025-01-02 15:30:00', '2025-01-02 15:35:00', '2025-01-03 12:15:00', NULL,
 'YT1122334455', '圆通速递', '外出携带使用', '蜂窝版，适合移动办公'),

-- 订单23: 已完成的订单
('ORD2025010400023', 'user023', '刘五', '13800138023', '银川市兴安区解放东街1号银川商城',
 'delivered', 'normal', 'bank_card', 'paid',
 'AirPods Pro 2 USB-C', 'APP2C', '耳机', '苹果AirPods Pro第二代，USB-C接口',
 1, 1899.00, 1899.00, 0.00, 0.00, 190.00, 2089.00,
 '2024-12-31 10:20:00', '2024-12-31 10:25:00', '2025-01-01 14:30:00', '2025-01-02 16:45:00',
 'ST1122334455', '申通快递', '新年新装备', '跨年订单，已确认收货'),

-- 订单24: 已取消的订单
('ORD2025010400024', 'user024', '赵六', '13800138024', '西宁市城中区西大街40号王府井百货',
 'cancelled', 'normal', 'wechat', 'refunded',
 'iPhone 15 Pro 512GB', 'IP15P512G', '手机', '苹果iPhone 15 Pro，512GB存储，原色钛金属',
 1, 10999.00, 10999.00, 0.00, 0.00, 1100.00, 12099.00,
 '2025-01-01 18:30:00', '2025-01-01 18:35:00', NULL, NULL,
 NULL, NULL, '预算不够了', '客户预算不足，取消订单'),

-- 订单25: 已确认的订单
('ORD2025010400025', 'user025', '孙七', '13800138025', '乌鲁木齐市天山区中山路317号新疆商贸大厦',
 'confirmed', 'normal', 'cash_on_delivery', 'unpaid',
 'Apple Vision Pro 标准版', 'AVPSTD', 'AR/VR设备', '苹果Vision Pro标准版，混合现实头显',
 1, 29999.00, 29999.00, 0.00, 0.00, 3000.00, 32999.00,
 '2025-01-03 11:10:00', '2025-01-03 11:15:00', NULL, NULL,
 NULL, NULL, '体验最新科技', '高价值商品，货到付款'),

-- 订单26: 处理中的订单
('ORD2025010400026', 'user026', '周八', '13800138026', '呼和浩特市新城区中山东路7号维多利商厦',
 'processing', 'bulk', 'alipay', 'paid',
 'iPhone 15 x20台', 'IP15x20', '手机', '苹果iPhone 15，批量采购20台，黑色',
 20, 5999.00, 119980.00, 0.00, 0.00, 12000.00, 131980.00,
 '2025-01-02 13:45:00', '2025-01-02 13:50:00', NULL, NULL,
 NULL, NULL, '企业年终奖采购', '企业福利采购，大批量订单'),

-- 订单27: 已发货的订单
('ORD2025010400027', 'user027', '吴九', '13800138027', '拉萨市城关区北京中路28号拉萨百货大楼',
 'shipped', 'rush', 'wechat', 'paid',
 'MacBook Pro 16英寸 M3 Max', 'MBP16M3M', '笔记本电脑', '苹果MacBook Pro 16英寸，M3 Max芯片',
 1, 26999.00, 26999.00, 50.00, 0.00, 2700.00, 29749.00,
 '2025-01-03 07:30:00', '2025-01-03 07:35:00', '2025-01-03 19:20:00', NULL,
 'SF6655443322', '顺丰速运', '高原地区，请小心包装', '偏远地区加急配送'),

-- 订单28: 已完成的订单
('ORD2025010400028', 'user028', '郑十', '13800138028', '海口市龙华区滨海大道29号海口国际商业中心',
 'delivered', 'normal', 'bank_card', 'paid',
 'iPad Pro 12.9英寸 M4', 'IPAD129M4', '平板电脑', '苹果iPad Pro 12.9英寸，M4芯片，最新版本',
 1, 9999.00, 9999.00, 0.00, 0.00, 1000.00, 10999.00,
 '2024-12-27 16:20:00', '2024-12-27 16:25:00', '2024-12-28 11:15:00', '2024-12-30 09:30:00',
 'HT6655443322', '汇通快递', '商务办公', '商务订单，已正常使用'),

-- 订单29: 待确认的订单
('ORD2025010400029', 'user029', '陈一', '13800138029', '银川市兴安区解放东街85号新华百货',
 'pending', 'normal', 'credit_card', 'unpaid',
 'Apple Watch Ultra 2', 'AWU2', '智能手表', '苹果Apple Watch Ultra 2，钛金属表壳',
 1, 6299.00, 6299.00, 0.00, 0.00, 630.00, 6929.00,
 '2025-01-03 16:15:00', NULL, NULL, NULL,
 NULL, NULL, '户外运动使用', '运动手表，需确认库存'),

-- 订单30: 已确认的订单
('ORD2025010400030', 'user030', '李二', '13800138030', '贵阳市南明区中华南路18号贵阳国贸广场',
 'confirmed', 'normal', 'cash_on_delivery', 'unpaid',
 'Mac mini M4', 'MMM4', '台式电脑', '苹果Mac mini，M4芯片，迷你台式机',
 1, 4499.00, 4499.00, 0.00, 0.00, 450.00, 4949.00,
 '2025-01-03 12:50:00', '2025-01-03 12:55:00', NULL, NULL,
 NULL, NULL, '家庭办公使用', '迷你电脑，货到付款');

