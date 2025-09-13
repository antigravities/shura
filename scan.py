import wmi
from . import db
from os import listdir, path
import vdf

class Scan:
    def __init__(self, volume):
        if not volume.endswith(':'):
            raise ValueError("Volume must end with ':'")

        self.volume = volume
        self.wmi = wmi.WMI()

        for volume in self.wmi.Win32_Volume():
            if volume.DriveLetter == self.volume:
                self.guid = volume.DeviceID
                self.label = volume.Label
                break

        if not hasattr(self, 'guid'):
            raise ValueError(f"Volume {self.volume} not found")

    def volumes():
        c = wmi.WMI()
        volumes = []

        for volume in c.Win32_Volume():
            if volume.DriveLetter:
                volumes.append((volume.DriveLetter, volume.Label or "No Label", volume.DeviceID))

        return volumes

    def volume_available(id):
        c = wmi.WMI()

        for volume in c.Win32_Volume():
            if volume.DeviceID == id:
                return (volume.DriveLetter, volume.Label or "No Label", volume.DeviceID)

        return False

    def scan(self):
        apps = 0
        depots = 0

        with db.session() as session:
            if not session.get(db.Volume, self.guid):
                volume = db.Volume(id=self.guid, label=self.label)
                session.add(volume)
                session.commit()
            else:
                volume = session.get(db.Volume, self.guid)

            for app in session.query(db.Application).filter_by(volume=volume).all():
                session.delete(app)
            session.commit()
            
            for dir in listdir(self.volume + '\\'):
                if path.exists(path.join(self.volume, dir, "sku.sis")):
                    with open(path.join(self.volume, dir, "sku.sis"), 'r', encoding='utf-8') as f:
                        data = vdf.load(f)

                        if not data.get('sku') or not data['sku'].get('apps'):
                            continue
                        
                        for app in data['sku']['apps'].values():
                            app = db.Application(
                                appid=app,
                                name=data['sku']['name'],
                                volume=volume,
                                location=dir
                            )

                            apps += 1
                            session.add(app)

                            for depot in data['sku']['depots'].values():
                                manifest = db.Manifest(
                                    application=app,
                                    depot=depot,
                                    manifest=data['sku']['manifests'].get(depot)
                                )

                                session.add(manifest)
                                depots += 1

                        session.commit()

        return apps, depots