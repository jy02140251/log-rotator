# log-rotator

A lightweight Python log rotation and archival tool with compression support and configurable retention policies.

## Features

- **Size-based rotation**: Rotate when log file exceeds threshold
- **Time-based rotation**: Rotate on schedule (hourly/daily/weekly)
- **Compression**: gzip/bz2 compression for archived logs
- **Retention**: Auto-delete logs older than N days
- **Pattern matching**: Process logs matching glob patterns
- **Dry-run mode**: Preview rotations without executing

## Usage

```bash
python rotator.py /var/log/app/*.log --max-size 50M --compress gzip --retain 30
```

## As a library

```python
from rotator import LogRotator, RotationPolicy

policy = RotationPolicy(
    max_size_mb=50,
    max_age_days=30,
    compress='gzip'
)

rotator = LogRotator(policy)
rotator.rotate('/var/log/app/')
```

## Requirements

- Python 3.8+
- No external dependencies

## License

MIT