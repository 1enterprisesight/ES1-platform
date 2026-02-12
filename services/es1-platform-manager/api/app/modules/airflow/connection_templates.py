"""Connection type templates with field definitions for the Connection Editor."""

from typing import Any

# Field type constants
TEXT = "text"
NUMBER = "number"
PASSWORD = "password"
TEXTAREA = "textarea"
SELECT = "select"

# Category constants
DATABASE = "database"
DATA_WAREHOUSE = "data_warehouse"
NOSQL = "nosql"
CLOUD_STORAGE = "cloud_storage"
API = "api"
MESSAGING = "messaging"
INFRASTRUCTURE = "infrastructure"
AI_ML = "ai_ml"

CATEGORIES = {
    DATABASE: "Databases",
    DATA_WAREHOUSE: "Data Warehouses",
    NOSQL: "NoSQL / Search",
    CLOUD_STORAGE: "Cloud Storage",
    API: "APIs",
    MESSAGING: "Messaging / Streaming",
    INFRASTRUCTURE: "Infrastructure",
    AI_ML: "AI / ML",
}

# Standard field builders for reuse
_host_field = lambda placeholder="db.example.com": {
    "name": "host", "label": "Host", "type": TEXT,
    "required": True, "placeholder": placeholder,
}
_port_field = lambda default: {
    "name": "port", "label": "Port", "type": NUMBER,
    "required": False, "placeholder": str(default),
}
_schema_field = lambda placeholder="mydb", label="Database": {
    "name": "schema", "label": label, "type": TEXT,
    "required": False, "placeholder": placeholder,
}
_login_field = lambda placeholder="user": {
    "name": "login", "label": "Username", "type": TEXT,
    "required": False, "placeholder": placeholder,
}
_password_field = {
    "name": "password", "label": "Password", "type": PASSWORD, "required": False,
}
_extra_field = {
    "name": "extra", "label": "Extra (JSON)", "type": TEXTAREA,
    "required": False, "placeholder": '{"key": "value"}',
}


CONNECTION_TEMPLATES: list[dict[str, Any]] = [
    # =========================================================================
    # Databases
    # =========================================================================
    {
        "conn_type": "postgres",
        "display_name": "PostgreSQL",
        "description": "Connect to a PostgreSQL database",
        "category": DATABASE,
        "default_port": 5432,
        "fields": [
            _host_field(),
            _port_field(5432),
            _schema_field("mydb"),
            _login_field("postgres"),
            _password_field,
        ],
        "extra_schema": {"sslmode": "prefer"},
    },
    {
        "conn_type": "mysql",
        "display_name": "MySQL",
        "description": "Connect to a MySQL database",
        "category": DATABASE,
        "default_port": 3306,
        "fields": [
            _host_field(),
            _port_field(3306),
            _schema_field("mydb"),
            _login_field("root"),
            _password_field,
        ],
        "extra_schema": {"charset": "utf8mb4"},
    },
    {
        "conn_type": "mssql",
        "display_name": "Microsoft SQL Server",
        "description": "Connect to a Microsoft SQL Server database",
        "category": DATABASE,
        "default_port": 1433,
        "fields": [
            _host_field(),
            _port_field(1433),
            _schema_field("master"),
            _login_field("sa"),
            _password_field,
        ],
        "extra_schema": {},
    },
    {
        "conn_type": "snowflake",
        "display_name": "Snowflake",
        "description": "Connect to Snowflake data warehouse",
        "category": DATABASE,
        "default_port": None,
        "fields": [
            {"name": "host", "label": "Account URL", "type": TEXT, "required": True, "placeholder": "account.snowflakecomputing.com"},
            _schema_field("my_database"),
            _login_field("snowflake_user"),
            _password_field,
            {"name": "extra", "label": "Extra (JSON)", "type": TEXTAREA, "required": False, "placeholder": '{"warehouse": "COMPUTE_WH", "role": "SYSADMIN", "schema": "PUBLIC"}'},
        ],
        "extra_schema": {"warehouse": "COMPUTE_WH", "role": "SYSADMIN", "schema": "PUBLIC"},
    },
    {
        "conn_type": "google_cloud_platform",
        "display_name": "BigQuery / GCP",
        "description": "Connect to Google Cloud Platform (BigQuery, GCS, etc.)",
        "category": DATABASE,
        "default_port": None,
        "fields": [
            {"name": "extra", "label": "Keyfile JSON or Extra", "type": TEXTAREA, "required": True, "placeholder": '{"extra__google_cloud_platform__project": "my-project", "extra__google_cloud_platform__key_path": "/path/to/key.json"}'},
        ],
        "extra_schema": {"extra__google_cloud_platform__project": "", "extra__google_cloud_platform__num_retries": 5},
    },
    {
        "conn_type": "redshift",
        "display_name": "Amazon Redshift",
        "description": "Connect to Amazon Redshift data warehouse",
        "category": DATABASE,
        "default_port": 5439,
        "fields": [
            _host_field("cluster.region.redshift.amazonaws.com"),
            _port_field(5439),
            _schema_field("dev"),
            _login_field("awsuser"),
            _password_field,
        ],
        "extra_schema": {},
    },
    {
        "conn_type": "oracle",
        "display_name": "Oracle",
        "description": "Connect to an Oracle database",
        "category": DATABASE,
        "default_port": 1521,
        "fields": [
            _host_field(),
            _port_field(1521),
            _schema_field("ORCL", label="Service Name"),
            _login_field("system"),
            _password_field,
        ],
        "extra_schema": {},
    },
    # =========================================================================
    # Data Warehouses
    # =========================================================================
    {
        "conn_type": "databricks",
        "display_name": "Databricks",
        "description": "Connect to Databricks workspace",
        "category": DATA_WAREHOUSE,
        "default_port": 443,
        "fields": [
            {"name": "host", "label": "Workspace URL", "type": TEXT, "required": True, "placeholder": "adb-123456.azuredatabricks.net"},
            _port_field(443),
            {"name": "password", "label": "Access Token", "type": PASSWORD, "required": True},
            {"name": "extra", "label": "Extra (JSON)", "type": TEXTAREA, "required": False, "placeholder": '{"http_path": "/sql/1.0/warehouses/abc123"}'},
        ],
        "extra_schema": {"http_path": ""},
    },
    {
        "conn_type": "spark",
        "display_name": "Apache Spark",
        "description": "Connect to Apache Spark via Thrift server",
        "category": DATA_WAREHOUSE,
        "default_port": 10000,
        "fields": [
            _host_field("spark-master"),
            _port_field(10000),
            _login_field("hive"),
            _password_field,
        ],
        "extra_schema": {},
    },
    {
        "conn_type": "trino",
        "display_name": "Trino / Presto",
        "description": "Connect to Trino or Presto query engine",
        "category": DATA_WAREHOUSE,
        "default_port": 8080,
        "fields": [
            _host_field("trino-coordinator"),
            _port_field(8080),
            _schema_field("hive", label="Catalog"),
            _login_field("trino"),
            _password_field,
        ],
        "extra_schema": {},
    },
    # =========================================================================
    # NoSQL / Search
    # =========================================================================
    {
        "conn_type": "mongo",
        "display_name": "MongoDB",
        "description": "Connect to a MongoDB database",
        "category": NOSQL,
        "default_port": 27017,
        "fields": [
            _host_field("mongo-host"),
            _port_field(27017),
            _schema_field("mydb"),
            _login_field("mongo"),
            _password_field,
        ],
        "extra_schema": {},
    },
    {
        "conn_type": "elasticsearch",
        "display_name": "Elasticsearch",
        "description": "Connect to an Elasticsearch cluster",
        "category": NOSQL,
        "default_port": 9200,
        "fields": [
            _host_field("elasticsearch"),
            _port_field(9200),
            _login_field("elastic"),
            _password_field,
        ],
        "extra_schema": {},
    },
    {
        "conn_type": "cassandra",
        "display_name": "Apache Cassandra",
        "description": "Connect to an Apache Cassandra cluster",
        "category": NOSQL,
        "default_port": 9042,
        "fields": [
            _host_field("cassandra-host"),
            _port_field(9042),
            _schema_field("my_keyspace", label="Keyspace"),
            _login_field("cassandra"),
            _password_field,
        ],
        "extra_schema": {},
    },
    # =========================================================================
    # Cloud Storage
    # =========================================================================
    {
        "conn_type": "aws",
        "display_name": "AWS S3",
        "description": "Connect to Amazon S3 and AWS services",
        "category": CLOUD_STORAGE,
        "default_port": None,
        "fields": [
            {"name": "login", "label": "AWS Access Key ID", "type": TEXT, "required": False, "placeholder": "AKIAIOSFODNN7EXAMPLE"},
            {"name": "password", "label": "AWS Secret Access Key", "type": PASSWORD, "required": False},
            {"name": "extra", "label": "Extra (JSON)", "type": TEXTAREA, "required": False, "placeholder": '{"region_name": "us-east-1"}'},
        ],
        "extra_schema": {"region_name": "us-east-1"},
    },
    {
        "conn_type": "google_cloud_platform",
        "display_name": "Google Cloud Storage",
        "description": "Connect to Google Cloud Storage",
        "category": CLOUD_STORAGE,
        "default_port": None,
        "fields": [
            {"name": "extra", "label": "Keyfile JSON or Extra", "type": TEXTAREA, "required": True, "placeholder": '{"extra__google_cloud_platform__project": "my-project"}'},
        ],
        "extra_schema": {"extra__google_cloud_platform__project": ""},
    },
    {
        "conn_type": "wasb",
        "display_name": "Azure Blob Storage",
        "description": "Connect to Azure Blob Storage",
        "category": CLOUD_STORAGE,
        "default_port": None,
        "fields": [
            {"name": "login", "label": "Storage Account Name", "type": TEXT, "required": True, "placeholder": "mystorageaccount"},
            {"name": "password", "label": "Storage Account Key", "type": PASSWORD, "required": True},
        ],
        "extra_schema": {},
    },
    # =========================================================================
    # APIs
    # =========================================================================
    {
        "conn_type": "http",
        "display_name": "HTTP / REST API",
        "description": "Connect to an HTTP or REST API endpoint",
        "category": API,
        "default_port": 443,
        "fields": [
            {"name": "host", "label": "Base URL", "type": TEXT, "required": True, "placeholder": "https://api.example.com"},
            _port_field(443),
            _login_field(""),
            _password_field,
            {"name": "extra", "label": "Headers (JSON)", "type": TEXTAREA, "required": False, "placeholder": '{"Authorization": "Bearer token"}'},
        ],
        "extra_schema": {},
    },
    {
        "conn_type": "generic",
        "display_name": "Generic",
        "description": "Generic connection for custom integrations",
        "category": API,
        "default_port": None,
        "fields": [
            _host_field(""),
            _port_field(0),
            _schema_field("", label="Schema"),
            _login_field(""),
            _password_field,
            _extra_field,
        ],
        "extra_schema": {},
    },
    # =========================================================================
    # Messaging / Streaming
    # =========================================================================
    {
        "conn_type": "slack",
        "display_name": "Slack",
        "description": "Connect to Slack workspace",
        "category": MESSAGING,
        "default_port": None,
        "fields": [
            {"name": "password", "label": "Bot Token", "type": PASSWORD, "required": True, "placeholder": "xoxb-..."},
        ],
        "extra_schema": {},
    },
    {
        "conn_type": "smtp",
        "display_name": "Email / SMTP",
        "description": "Connect to an SMTP server for sending emails",
        "category": MESSAGING,
        "default_port": 587,
        "fields": [
            _host_field("smtp.gmail.com"),
            _port_field(587),
            _login_field("user@example.com"),
            _password_field,
        ],
        "extra_schema": {},
    },
    {
        "conn_type": "kafka",
        "display_name": "Apache Kafka",
        "description": "Connect to an Apache Kafka cluster",
        "category": MESSAGING,
        "default_port": 9092,
        "fields": [
            _host_field("kafka-broker"),
            _port_field(9092),
            {"name": "extra", "label": "Extra (JSON)", "type": TEXTAREA, "required": False, "placeholder": '{"bootstrap.servers": "broker1:9092,broker2:9092"}'},
        ],
        "extra_schema": {"bootstrap.servers": ""},
    },
    # =========================================================================
    # Infrastructure
    # =========================================================================
    {
        "conn_type": "ssh",
        "display_name": "SSH",
        "description": "Connect to a remote server via SSH",
        "category": INFRASTRUCTURE,
        "default_port": 22,
        "fields": [
            _host_field("server.example.com"),
            _port_field(22),
            _login_field("ubuntu"),
            _password_field,
            {"name": "extra", "label": "Extra (JSON)", "type": TEXTAREA, "required": False, "placeholder": '{"key_file": "/path/to/key.pem"}'},
        ],
        "extra_schema": {},
    },
    {
        "conn_type": "ftp",
        "display_name": "FTP / SFTP",
        "description": "Connect to an FTP or SFTP server",
        "category": INFRASTRUCTURE,
        "default_port": 21,
        "fields": [
            _host_field("ftp.example.com"),
            _port_field(21),
            _login_field("ftpuser"),
            _password_field,
        ],
        "extra_schema": {},
    },
    # =========================================================================
    # AI / ML
    # =========================================================================
    {
        "conn_type": "openai",
        "display_name": "OpenAI",
        "description": "Connect to OpenAI API",
        "category": AI_ML,
        "default_port": None,
        "fields": [
            {"name": "password", "label": "API Key", "type": PASSWORD, "required": True, "placeholder": "sk-..."},
            {"name": "extra", "label": "Extra (JSON)", "type": TEXTAREA, "required": False, "placeholder": '{"organization": "org-..."}'},
        ],
        "extra_schema": {},
    },
    {
        "conn_type": "pinecone",
        "display_name": "Pinecone",
        "description": "Connect to Pinecone vector database",
        "category": AI_ML,
        "default_port": None,
        "fields": [
            {"name": "host", "label": "Environment", "type": TEXT, "required": True, "placeholder": "us-east1-gcp"},
            {"name": "password", "label": "API Key", "type": PASSWORD, "required": True},
        ],
        "extra_schema": {},
    },
    {
        "conn_type": "weaviate",
        "display_name": "Weaviate",
        "description": "Connect to Weaviate vector database",
        "category": AI_ML,
        "default_port": 8080,
        "fields": [
            _host_field("weaviate.example.com"),
            _port_field(8080),
            {"name": "password", "label": "API Key", "type": PASSWORD, "required": False},
        ],
        "extra_schema": {},
    },
    {
        "conn_type": "chroma",
        "display_name": "ChromaDB",
        "description": "Connect to ChromaDB vector database",
        "category": AI_ML,
        "default_port": 8000,
        "fields": [
            _host_field("localhost"),
            _port_field(8000),
        ],
        "extra_schema": {},
    },
    {
        "conn_type": "huggingface",
        "display_name": "Hugging Face",
        "description": "Connect to Hugging Face API",
        "category": AI_ML,
        "default_port": None,
        "fields": [
            {"name": "password", "label": "API Token", "type": PASSWORD, "required": True, "placeholder": "hf_..."},
        ],
        "extra_schema": {},
    },
]


def get_connection_templates() -> list[dict[str, Any]]:
    """Get all connection templates."""
    return CONNECTION_TEMPLATES


def get_connection_template(conn_type: str) -> dict[str, Any] | None:
    """Get a specific connection template by conn_type.

    Returns the first matching template, or None if not found.
    """
    for template in CONNECTION_TEMPLATES:
        if template["conn_type"] == conn_type:
            return template
    return None


def get_template_categories() -> dict[str, str]:
    """Get the category ID to display name mapping."""
    return CATEGORIES.copy()
