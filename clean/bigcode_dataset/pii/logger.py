
import os
import logging
from pii_args import parseArgs

args = parseArgs()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# log_filepath=os.path.join(args.project_dirpath,'shells/nohups/pii.log')
log_filepath=os.environ['nohup_pii_logger_path']
# log_filepath=os.path.join(args.project_dirpath,'shells/nohups/pii.log')
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.INFO,
    handlers=[
    logging.FileHandler(log_filepath),
    logging.StreamHandler()
]
)