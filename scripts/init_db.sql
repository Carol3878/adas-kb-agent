-- 模块一:DBC信号字典库
CREATE TABLE IF NOT EXISTS signal_dictionary (
    id SERIAL PRIMARY KEY,
    standard_name TEXT,
    cn_aliases TEXT[] DEFAULT '{}',
    dbc_message_name TEXT,
    dbc_signal_name TEXT,
    unit TEXT,
    valid_min FLOAT,
    valid_max FLOAT,
    ck_column_name TEXT,
    description TEXT,
    source TEXT,
    review_status TEXT DEFAULT 'needs_review',
    UNIQUE (dbc_message_name, dbc_signal_name)
);

-- 模块二:云端数据描述库(由CK自动内省填充,不是文档解析)
CREATE TABLE IF NOT EXISTS db_schema (
    id SERIAL PRIMARY KEY,
    database_name TEXT,
    table_name TEXT,
    column_name TEXT,
    data_type TEXT,
    comment TEXT,
    is_partition_key BOOLEAN DEFAULT false,
    is_sorting_key BOOLEAN DEFAULT false,
    is_primary_key BOOLEAN DEFAULT false,
    UNIQUE (database_name, table_name, column_name)
);

-- 模块三:业务规范与规则断言库(草稿表 + 正式表)
CREATE TABLE IF NOT EXISTS business_rules_draft (
    id SERIAL PRIMARY KEY,
    record_type TEXT CHECK (record_type IN ('spec_assertion', 'kpi_metric')),
    name TEXT,
    natural_language_desc TEXT,
    logic_expression TEXT,
    required_signals TEXT[] DEFAULT '{}',
    confidence FLOAT,
    source_doc TEXT,
    review_status TEXT DEFAULT 'needs_review',
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS business_rules (
    id SERIAL PRIMARY KEY,
    record_type TEXT CHECK (record_type IN ('spec_assertion', 'kpi_metric')),
    name TEXT UNIQUE,
    natural_language_desc TEXT,
    logic_expression TEXT,
    required_signals TEXT[] DEFAULT '{}',
    source_doc TEXT,
    promoted_at TIMESTAMP DEFAULT now()
);

-- 模块四:车型版本路由表(人工登记为主)
CREATE TABLE IF NOT EXISTS vehicle_routing (
    id SERIAL PRIMARY KEY,
    car_model TEXT,
    version_min TEXT,
    version_max TEXT,
    dbc_file_name TEXT,
    ck_table_name TEXT,
    es_index_name TEXT,
    UNIQUE (car_model, version_min, version_max)
);

-- 法规索引表(模块五的轻量伴生表)
CREATE TABLE IF NOT EXISTS regulation_index (
    id SERIAL PRIMARY KEY,
    reg_number TEXT UNIQUE,
    reg_name TEXT,
    status TEXT CHECK (status IN ('现行', '征求意见稿', '起草组讨论稿')),
    applicable_level TEXT,
    source_chunk_ids TEXT[] DEFAULT '{}'
);
