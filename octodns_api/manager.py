#
#
#

from logging import getLogger

from octodns.manager import Manager
from octodns.record import Record
from octodns.zone import Zone


class ApiManagerException(Exception):
    pass


class ApiManager:
    '''
    Wrapper around octoDNS Manager for API operations

    Provides high-level methods for zone and record CRUD operations
    '''

    log = getLogger('ApiManager')

    def __init__(self, config_file):
        '''
        Initialize API Manager

        :param config_file: Path to octoDNS configuration file
        :type config_file: str
        '''
        self.config_file = config_file
        self.manager = Manager(config_file)

    def list_zones(self):
        '''
        List all configured zones

        :return: List of zone names
        '''
        return list(self.manager.config['zones'].keys())

    def get_zone(self, zone_name):
        '''
        Get a zone with all its records from the configured sources

        :param zone_name: Name of the zone (e.g., 'example.com.')
        :type zone_name: str
        :return: Zone object populated with records
        '''
        if not zone_name.endswith('.'):
            zone_name = f'{zone_name}.'

        zones_config = self.manager.config['zones']
        if zone_name not in zones_config:
            raise ApiManagerException(f'Zone {zone_name} not configured')

        zone_config = zones_config[zone_name]
        sources = zone_config.get('sources', [])

        if not sources:
            raise ApiManagerException(
                f'Zone {zone_name} has no sources configured'
            )

        # Create zone and populate from first source
        zone = Zone(zone_name, [])
        source_name = sources[0]
        source = self.manager.providers.get(source_name)

        if not source:
            raise ApiManagerException(f'Source {source_name} not found')

        source.populate(zone, lenient=False)

        return zone

    def get_record(self, zone_name, record_name, record_type):
        '''
        Get a specific record from a zone

        :param zone_name: Name of the zone
        :param record_name: Name of the record (e.g., 'www' or '' for apex)
        :param record_type: Record type (e.g., 'A', 'CNAME')
        :return: Record object or None
        '''
        zone = self.get_zone(zone_name)

        for record in zone.records:
            if record.name == record_name and record._type == record_type:
                return record

        return None

    def create_or_update_record(self, zone_name, record_data):
        '''
        Create or update a record in a zone

        :param zone_name: Name of the zone
        :param record_data: Record data dictionary
        :return: Tuple of (record, changes_applied)
        '''
        if not zone_name.endswith('.'):
            zone_name = f'{zone_name}.'

        zones_config = self.manager.config['zones']
        if zone_name not in zones_config:
            raise ApiManagerException(f'Zone {zone_name} not configured')

        zone_config = zones_config[zone_name]
        targets = zone_config.get('targets', [])

        if not targets:
            raise ApiManagerException(
                f'Zone {zone_name} has no targets configured'
            )

        # Get current zone state
        zone = self.get_zone(zone_name)

        # Create new record from data
        record_name = record_data.get('name', '')
        new_record = Record.new(zone, record_name, record_data)

        # Add or replace record in zone
        zone.add_record(new_record, replace=True)

        # Create desired zone with the new/updated record
        desired = Zone(zone_name, [])
        desired.add_record(new_record)

        # Sync to targets
        target_name = targets[0]
        target = self.manager.providers.get(target_name)

        if not target:
            raise ApiManagerException(f'Target {target_name} not found')

        plan = target.plan(desired)

        if plan:
            target.apply(plan)
            return new_record, True

        return new_record, False

    def delete_record(self, zone_name, record_name, record_type):
        '''
        Delete a record from a zone

        :param zone_name: Name of the zone
        :param record_name: Name of the record
        :param record_type: Record type
        :return: True if deleted, False if not found
        '''
        if not zone_name.endswith('.'):
            zone_name = f'{zone_name}.'

        zones_config = self.manager.config['zones']
        if zone_name not in zones_config:
            raise ApiManagerException(f'Zone {zone_name} not configured')

        zone_config = zones_config[zone_name]
        targets = zone_config.get('targets', [])

        if not targets:
            raise ApiManagerException(
                f'Zone {zone_name} has no targets configured'
            )

        # Get current zone state
        zone = self.get_zone(zone_name)

        # Find the record to delete
        record_to_delete = None
        for record in zone.records:
            if record.name == record_name and record._type == record_type:
                record_to_delete = record
                break

        if not record_to_delete:
            return False

        # Create desired zone without the record (empty zone for this specific record)
        desired = Zone(zone_name, [])

        # Sync to targets
        target_name = targets[0]
        target = self.manager.providers.get(target_name)

        if not target:
            raise ApiManagerException(f'Target {target_name} not found')

        # Plan with empty desired zone will show deletion
        plan = target.plan(desired)

        if plan:
            target.apply(plan)
            return True

        return False

    def sync_zone(self, zone_name, dry_run=True):
        '''
        Sync a zone from sources to targets

        :param zone_name: Name of the zone
        :param dry_run: If True, only plan changes without applying
        :return: Dictionary with plan information
        '''
        if not zone_name.endswith('.'):
            zone_name = f'{zone_name}.'

        zones_config = self.manager.config['zones']
        if zone_name not in zones_config:
            raise ApiManagerException(f'Zone {zone_name} not configured')

        eligible_zones = [zone_name]
        result = self.manager.sync(
            eligible_zones=eligible_zones, dry_run=dry_run, force=False
        )

        return {'zone': zone_name, 'dry_run': dry_run, 'result': result}
