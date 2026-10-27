# PyMySQL is a pure-Python MySQL driver: no C compiler needed on any OS.
# It is registered here as "MySQLdb" so Django's MySQL backend can use it.
try:
    import pymysql

    pymysql.version_info = (2, 2, 1, "final", 0)  # satisfy Django's version check
    pymysql.install_as_MySQLdb()
except ImportError:  # mysqlclient may be installed instead
    pass
