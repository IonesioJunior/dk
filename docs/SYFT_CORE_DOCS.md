# Syft-Core Documentation

## Overview

Syft-Core is a foundational package providing essential utilities and abstractions for the OpenMined SyftBox platform. It offers client management, configuration handling, permission control, and specialized data types that support private, secure data operations within the Syft ecosystem.

This document covers the key components of the syft-core package, their functionality, and provides usage examples.

## Table of Contents

1. [Installation](#installation)
2. [Main Components](#main-components)
3. [Client](#client)
4. [Configuration](#configuration)
5. [Permissions](#permissions)
6. [URL Handling](#url-handling)
7. [Workspace Management](#workspace-management)
8. [Custom Types](#custom-types)
9. [Constants](#constants)
10. [Exception Handling](#exception-handling)
11. [Complete Examples](#complete-examples)

## Installation

```bash
pip install syft-core
```

## Main Components

The syft-core package exposes these primary components:

```python
from syft_core import Client, SyftClientConfig, SyftWorkspace, SyftBoxURL
```

These core classes provide the foundation for interacting with the SyftBox platform.

## Client

The `Client` class provides a lightweight interface for SyftBox applications, managing user-specific data and configuration.

### Key Features

- User identification through email
- Configuration file management
- Filesystem access for app data
- Datasite path management

### Example Usage

```python
from syft_core import Client, SyftClientConfig

# Create a client with explicit configuration
config = SyftClientConfig(
    email="user@example.com",
    data_dir="/path/to/data",
    server_url="https://syftbox.example.com"
)
client = Client(config)

# Get user email
user_email = client.email
print(f"Client user: {user_email}")

# Access configuration path
config_path = client.config_path
print(f"Configuration stored at: {config_path}")

# Get application data directory
app_data_path = client.app_data("my-app")
print(f"App data directory: {app_data_path}")

# Access user's datasite
datasite_path = client.my_datasite("dataset1")
print(f"Datasite path: {datasite_path}")

# Load client from existing configuration
loaded_client = Client.load()
```

## Configuration

The `SyftClientConfig` class handles all configuration settings for the SyftBox client.

### Key Features

- Environment variable support
- JSON-based configuration files
- Default configuration paths
- Migration from legacy configs

### Example Usage

```python
from syft_core import SyftClientConfig
from pathlib import Path

# Create configuration with explicit values
config = SyftClientConfig(
    email="user@example.com",
    data_dir=Path.home() / "syft_data",
    server_url="https://syftbox.openmined.org",
    client_url="http://localhost:8080",
    access_token="auth_token_12345"
)

# Save configuration to file
config.save(Path.home() / ".syft" / "config.json")

# Load from environment variables
env_config = SyftClientConfig.from_env()

# Load from file
loaded_config = SyftClientConfig.load(Path.home() / ".syft" / "config.json")

# Migrate from legacy configuration
migrated_config = SyftClientConfig.migrate(Path.home() / ".syft" / "legacy_config.json")
```

## Permissions

The permissions system implements fine-grained access control for files and directories.

### Key Components

- `PermissionRule`: Individual permission definitions
- `SyftPermission`: Collection of rules for a specific file
- `ComputedPermission`: Calculated effective permissions

### Permission Levels

- `CREATE`: Permission to create files
- `READ`: Permission to read files
- `WRITE`: Permission to modify files
- `ADMIN`: Administrative access

### Example Usage

```python
from syft_core.permissions import (
    PermissionRule, SyftPermission, ComputedPermission,
    CREATE, READ, WRITE, ADMIN
)
from pathlib import Path

# Define a permission rule for a specific user
rule1 = PermissionRule(
    path=Path("data/project1"),
    user="user@example.com",
    allow=[READ, WRITE]
)

# Define a rule with wildcard user
rule2 = PermissionRule(
    path=Path("data/public"),
    user="*",
    allow=[READ]
)

# Create a permission set for a file
file_permissions = SyftPermission(
    path=Path("data/project1/report.csv"),
    rules=[rule1, rule2]
)

# Load permissions from YAML file
from_file = SyftPermission.from_file(Path("permissions.yaml"))

# Check if a user has permission
user_email = "user@example.com"
can_write = WRITE in ComputedPermission(
    path=Path("data/project1/report.csv"),
    user=user_email,
    rules=[rule1, rule2]
).allow
```

## URL Handling

The `SyftBoxURL` class implements a custom URL scheme for Syft resources.

### Key Features

- Custom "syft://" protocol
- Email-based host component
- Path translation to local filesystem

### Example Usage

```python
from syft_core import SyftBoxURL

# Create a SyftBox URL
url = SyftBoxURL("syft://user@example.com/path/to/resource")

# Extract components
protocol = url.protocol  # "syft"
host = url.host  # "user@example.com"
path = url.path  # "/path/to/resource"

# Convert to local path
local_path = url.to_local_path()

# Generate HTTP parameters
http_params = url.http_params()

# Convert to HTTP request
http_url = url.to_http()
```

## Workspace Management

The `SyftWorkspace` class manages directory structures for client data.

### Key Features

- Standard directory structure
- Datasites, plugins, and API data organization
- Automatic directory creation

### Example Usage

```python
from syft_core import SyftWorkspace
from pathlib import Path

# Create a workspace
workspace = SyftWorkspace(Path.home() / "syft_data")

# Access subdirectories
datasites_dir = workspace.datasites_dir
plugins_dir = workspace.plugins_dir
apis_dir = workspace.apis_dir

# Ensure directories exist
workspace.mkdirs()

# Create all necessary subdirectories
import os
os.listdir(workspace.root_dir)  # Shows created directories
```

## Custom Types

The syft-core package defines specialized path and user types.

### Key Types

- `PathLike`: Type for path arguments
- `UserLike`: Type for user identifiers
- `RelativePath`: Validated relative path
- `AbsolutePath`: Validated absolute path

### Example Usage

```python
from syft_core.types import (
    to_path, should_be_relative, should_be_absolute,
    issubpath, RelativePath, AbsolutePath
)
from pathlib import Path

# Convert string to path
path_obj = to_path("~/data")

# Validate paths
rel_path = RelativePath("data/file.txt")  # Valid
try:
    rel_path = RelativePath("/absolute/path")  # Raises ValueError
except ValueError:
    print("Path must be relative")

abs_path = AbsolutePath("/absolute/path")  # Valid
try:
    abs_path = AbsolutePath("relative/path")  # Raises ValueError
except ValueError:
    print("Path must be absolute")

# Check subpath relationship
is_subpath = issubpath(Path("/data/project/file.txt"), Path("/data"))  # True
```

## Constants

The syft-core package defines various constants for default settings.

### Key Constants

- `DEFAULT_PORT`: 8080
- `DEFAULT_SERVER_URL`: "https://syftbox.openmined.org"
- `DEFAULT_CONFIG_DIR`: User's home directory + ".syft"
- `DEFAULT_DATA_DIR`: User's home directory + "syft-data"
- `PERM_FILE`: "syftperm.yaml"

### Example Usage

```python
from syft_core.constants import (
    DEFAULT_PORT, DEFAULT_SERVER_URL,
    DEFAULT_CONFIG_DIR, DEFAULT_DATA_DIR
)

# Use constants for configuration
import os
config_path = os.path.join(DEFAULT_CONFIG_DIR, "config.json")
server = f"http://localhost:{DEFAULT_PORT}"
```

## Exception Handling

The syft-core package provides custom exceptions for error handling.

### Key Exceptions

- `SyftBoxException`: Base exception for all Syft errors
- `ClientConfigException`: Configuration-related errors
- `PermissionParsingError`: Problems with permission parsing

### Example Usage

```python
from syft_core.exceptions import (
    SyftBoxException, ClientConfigException, PermissionParsingError
)

try:
    # Code that might raise exceptions
    config = load_config()
except ClientConfigException as e:
    print(f"Configuration error: {str(e)}")
except PermissionParsingError as e:
    print(f"Permission parsing error: {str(e)}")
except SyftBoxException as e:
    print(f"General Syft error: {str(e)}")
```

## Complete Examples

### Setting Up a Basic Client

```python
from syft_core import Client, SyftClientConfig, SyftWorkspace
from pathlib import Path

# Create configuration
config = SyftClientConfig(
    email="user@example.com",
    data_dir=Path.home() / "syft_data",
    server_url="https://syftbox.example.com"
)

# Save configuration
config.save()

# Create client
client = Client(config)

# Initialize workspace
workspace = SyftWorkspace(client.config.data_dir)
workspace.mkdirs()

# Access application data
app_data_path = client.app_data("my-analysis-app")
print(f"Application data will be stored at: {app_data_path}")
```

### Working with Permissions

```python
from syft_core.permissions import (
    PermissionRule, SyftPermission, CREATE, READ, WRITE, ADMIN
)
from pathlib import Path
import yaml

# Define permissions
rules = [
    PermissionRule(
        path=Path("project/data"),
        user="owner@example.com",
        allow=[CREATE, READ, WRITE, ADMIN]
    ),
    PermissionRule(
        path=Path("project/data"),
        user="analyst@example.com",
        allow=[READ]
    ),
    PermissionRule(
        path=Path("project/results"),
        user="*",
        allow=[READ]
    )
]

# Create permission objects
permissions = SyftPermission(
    path=Path("project"),
    rules=rules
)

# Save to YAML file
with open("permissions.yaml", "w") as f:
    yaml.dump(permissions.to_dict(), f)

# Load from YAML file
loaded_permissions = SyftPermission.from_file(Path("permissions.yaml"))
```

### Using SyftBox URLs

```python
from syft_core import SyftBoxURL, Client, SyftClientConfig

# Create client
config = SyftClientConfig.load()
client = Client(config)

# Create and use URLs
resource_url = SyftBoxURL(f"syft://{client.email}/dataset/file.csv")

# Convert to local path
local_path = resource_url.to_local_path()
print(f"Resource is stored at: {local_path}")

# Create HTTP URL for remote access
http_url = resource_url.to_http()
print(f"Resource can be accessed via: {http_url}")
```

## Version Information

The current version of the syft-core package is 0.1.0.