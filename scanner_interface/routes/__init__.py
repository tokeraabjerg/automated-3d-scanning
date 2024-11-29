#---------------------------------------------------------------------------
#  ?                                ABOUT
#  @author         :  
#  @repo           :  
#  @description    :  
#---------------------------------------------------------------------------
# routes/__init__.py

from .project_routes import project_bp
from .scan_routes import scan_bp
from .config_routes import config_bp
from .interface_routes import interface_bp 

__all__ = ['project_bp', 'scan_bp', 'config_bp', 'interface_bp']

