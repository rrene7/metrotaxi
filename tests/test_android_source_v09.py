"""Guardias de estructura del proyecto Android. NO sustituyen compilación ni pruebas en teléfono."""
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
APK=ROOT/'android-conductor'
JAVA=APK/'app/src/main/java/pa/metrotaxi/conductor'

class AndroidSourceGuards(unittest.TestCase):
    def test_android_manifest_location_consent_controls(self):
        manifest=(APK/'app/src/main/AndroidManifest.xml')
        root=ET.parse(manifest).getroot()
        ns='{http://schemas.android.com/apk/res/android}'
        permissions={p.get(ns+'name') for p in root.findall('uses-permission')}
        self.assertIn('android.permission.FOREGROUND_SERVICE_LOCATION', permissions)
        self.assertIn('android.permission.ACCESS_FINE_LOCATION', permissions)
        self.assertNotIn('android.permission.ACCESS_BACKGROUND_LOCATION', permissions)
        application=root.find('application')
        self.assertEqual('false',application.get(ns+'usesCleartextTraffic'))
        self.assertEqual('false',application.get(ns+'allowBackup'))
        services=application.findall('service')
        self.assertEqual(1,len(services))
        self.assertEqual('location',services[0].get(ns+'foregroundServiceType'))
        self.assertEqual('false',services[0].get(ns+'exported'))
    def test_native_access_is_isolated(self):
        activity=(JAVA/'MainActivity.java').read_text()
        service=(JAVA/'LocationTrackingService.java').read_text()
        api=(JAVA/'MetroApi.java').read_text()
        self.assertNotIn('addJavascriptInterface(',activity.replace('No se usa addJavascriptInterface:', ''))
        self.assertIn('MIXED_CONTENT_NEVER_ALLOW',activity)
        self.assertIn('setAllowFileAccess(false)',activity)
        self.assertIn('setSupportMultipleWindows(true)',activity)
        self.assertIn('START_NOT_STICKY',service)
        self.assertIn('LocationManager.GPS_PROVIDER',service)
        self.assertIn('getElapsedRealtimeNanos()',service)
        self.assertIn('driverSession()',api)
        self.assertIn('X-CSRF-Token',api)
        self.assertIn('CookieManager.getInstance()',api)
        self.assertIn('"https".equals(url.getProtocol())',api)
        self.assertIn('"/api/driver/location"',api)
        self.assertNotIn('password=',api.lower())
    def test_release_never_defaults_to_localhost(self):
        gradle=(APK/'app/build.gradle').read_text()
        self.assertIn('https://example.invalid',gradle)
        self.assertIn('metroBaseUrl',gradle)
        self.assertNotIn('127.0.0.1',gradle)
        self.assertIn('android:foregroundServiceType="location"',(APK/'app/src/main/AndroidManifest.xml').read_text())
    def test_work_route_and_documentation(self):
        route=(ROOT/'RUTA_DE_TRABAJO.md').read_text()
        self.assertIn('v0.9',route)
        self.assertTrue((ROOT/'docs/PLAN_PUBLICACION_V09.md').exists())

if __name__=='__main__':unittest.main()
