import ee
import geemap

from datetime import datetime

import os



# CONFIGURATION
EE_PROJECT = "user-project-id"
REGION_NAME = "Camarillo"
BBOX = [-119.1, 34.2, -118.9, 34.4]
PRE_FIRE_START = "2024-10-01"
PRE_FIRE_DATE = "2024-11-06"
POST_FIRE_START = "2024-12-01"
POST_FIRE_DATE = "2024-12-31"

print(f"\nStudy Area: {REGION_NAME}")
print(f"Coordinates: {BBOX}")
print(f"Date Range: {PRE_FIRE_DATE} to {POST_FIRE_DATE}")


try:
    ee.Initialize(project=EE_PROJECT)
    print("Google Earth Engine connected Successfully")
except:
    print("Google Earth Engine connection failed")
    print("Run: earthengine authenticate")

#Create Earth Engine geometry
region_of_interest = ee.Geometry.Rectangle(BBOX)

# Calculate area
area_sqm = region_of_interest.area().getInfo()
area_sqkm = area_sqm / 1_000_000
area_ha = area_sqm / 10000
print(f"Area: {area_sqkm:.2f} km²")
print(f"Area: {area_ha:.2f} ha")


#lets load our sentinel data

print("\n"+"="*50)
print("Loading Sentinel-2 Data")
print("="*50)

prefire_images = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterDate(PRE_FIRE_START, PRE_FIRE_DATE).filterBounds(
    region_of_interest
).filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))

postfire_images = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterDate(POST_FIRE_START, POST_FIRE_DATE).filterBounds(
    region_of_interest
).filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))


#count images found
pre_count = prefire_images.size().getInfo()
post_count = postfire_images.size().getInfo()
print(f"\nFound {pre_count}, {post_count} Sentinel-2 images")


if pre_count == 0 or post_count == 0:
    print(" No images found! Try:")
    print("  1. Expanding date range")
    print("  2. Increasing cloud cover threshold")
    print("  3. Checking coordinates")
    exit()

#Create a cloud free composite
pre_fire_image = prefire_images.median().clip(region_of_interest)
post_fire_image = postfire_images.median().clip(region_of_interest)

print(f"✅ Created cloud-free composite image for pre-fire images)")

#Calculate the spectral indices
print("\n" + "="*50)
print("STEP 2: Calculating Spectral Indices")
print("="*50)

#NBR
prefire_nir = pre_fire_image.select('B8')
prefire_swir = pre_fire_image.select('B12')

postfire_nir = post_fire_image.select('B8')
postfire_swir = post_fire_image.select('B12')

prefire_nbr = prefire_nir.subtract(prefire_swir).divide(prefire_nir.add(prefire_swir)).rename('PREFIRE_NBR')
postfire_nbr = postfire_nir.subtract(postfire_swir).divide(postfire_nir.add(postfire_swir)).rename('POSTFIRE_NBR')

print("✓ NBR calculated")

#calculate dnbr

dnbr = prefire_nbr.subtract(postfire_nbr).rename('DNBR')

#classify dnbr

severity = (
    dnbr.lt(0.05).multiply(0).where(dnbr.gt(0.05).And(dnbr.lt(0.27)), 1).
    where(dnbr.gt(0.27).And(dnbr.lt(0.439)), 2).
    where(dnbr.gt(0.439).And(dnbr.lt(0.659)), 3).
    where(dnbr.gt(0.66), 4)
).rename('SEVERITY')

severity_vis = {
    'min': 0,
    'max': 4,
    'palette': [
        '#00ff00',  # Unburned
        '#ffff00',  # Low
        '#ff9900',  # Moderate-Low
        '#ff0000',  # Moderate-High
        '#7a0000'   # High
    ]
}

#Interactive map
print("\n" + "="*50)
print("STEP 4: Creating Interactive Map")
print("="*50)

center_lat = (BBOX[1] + BBOX[3]) / 2
center_lon = (BBOX[0] + BBOX[2]) / 2
Map = geemap.Map(center=(center_lat, center_lon), zoom=10)

nbr_vis = {
    'min': -1,
    'max': 1,
    'palette': ['brown', 'yellow', 'green']
}
dnbr_vis = {
    'min': -1,
    'max': 1,
    'palette': ['brown', 'yellow', 'orange' ,'red']
}
legend_dict = {
    'Unburned': '#00ff00',
    'Low severity': '#ffff00',
    'Moderate-Low': '#ff9900',
    'Moderate-High': '#ff0000',
    'High severity': '#7a0000'
}
#Add NBR Layer
Map.add_basemap('HYBRID')
Map.addLayer(prefire_nbr, nbr_vis, 'PREFIRE_NBR')
Map.addLayer(postfire_nbr, nbr_vis, 'POSTFIRE_NBR')
Map.addLayer(dnbr, dnbr_vis, 'DNBR')
Map.addLayer(severity, severity_vis, 'SEVERITY')
Map.add_legend(title='Burn Severity (dNBR)', legend_dict=legend_dict, position='bottomright')




map_path = f"./outputs/map_{REGION_NAME}.html"
Map.to_html(map_path)
print(f"Interactive map saved: {map_path}")


# Create an enhanced HTML dashboard
print("\n" + "="*50)
print("STEP 7: Creating Interactive HTML Dashboard")
print("="*50)

# Create custom HTML with controls
dashboard_html = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wildfire Dashboard - {REGION_NAME}</title>
    <style>
        
        *{{
            box-sizing: border-box;
            font-family: Arial, sans-serif;
            
        }}
        
        body {{
            background-color: #f5f5f5;
            padding: 0;
            margin: 0;
            
            width: 100%;
            height: 95vh;
            overflow: hidden;
        }}
        
        .main-container {{
            display: flex;
            flex-direction: row;
            height: 95vh;
            padding: 10px;
        }}
        
        .side-bar {{
            width: 300px;
            height: calc(98vh - 20px);
            background-color: blanchedalmond;
            padding: 20px;
            margin: 10px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow-y: auto;
            text-align: justify;
            
        }}
        
        .main-content {{
            width: calc(100% - 340px);
            height: calc(98vh - 20px);
            background-color: beige;
            padding: 20px;
            margin: 10px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
        }}
        
        .header {{
            width: 100%;
            background-color: burlywood;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
        }}   
        
        .header .dashboard-title {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 22px;
            font-weight: bold;
            font-style: italic;
            margin-bottom: 10px;
            color: #333;
        }}
        
        .content {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        
        .container {{
            background-color: rgba(255, 255, 255, 0.8);
            padding: 15px;
            border-radius: 8px;
            
            font-size: 12px;
            color: #333;
        }}
        
        .info-box {{
            background-color: rgba(255, 255, 255, 0.8);
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .info-box h3 {{
            color: #8B4513;
            margin-top: 0;
            margin-bottom: 10px;
            font-size: 18px;
        }}
        
        .info-box p {{
            margin: 8px 0;
            line-height: 1.5;
            color: #333;
        }}
        
        .footer {{
            background-color: rgba(255, 255, 255, 0.8);
            padding: 15px;
            border-radius: 8px;
            font-size: 12px;
            color: #666;
            text-align: center;
            margin-top: 10px;
        }}
        
        .footer p {{
            margin: 5px 0;
        }}
        
        .map {{
            width: 100%;
            height: 100%;
            border-radius: 8px;
            overflow: hidden;
        }}
        
        iframe {{
            width: 100%;
            height: 100%;
            border: none;
            display: block;
        }}
        
        /* Custom scrollbar */
        .side-bar::-webkit-scrollbar {{
            width: 8px;
        }}
        
        .side-bar::-webkit-scrollbar-track {{
            background: rgba(255, 255, 255, 0.3);
            border-radius: 10px;
        }}
        
        .side-bar::-webkit-scrollbar-thumb {{
            background: rgba(139, 69, 19, 0.5);
            border-radius: 10px;
        }}
        
        .side-bar::-webkit-scrollbar-thumb:hover {{
            background: rgba(139, 69, 19, 0.7);
        }}
    </style>
</head>
<body>
    <div class="main-container">
        <div class="side-bar">
            <div class="header">
                <div class="dashboard-title">🔥 Wildfire Burn Severity Dashboard</div>
            </div>
            <div class="content">
                <div class="container">
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 8px;">Region: {REGION_NAME}</div>
                    <div>Analysis Period: {PRE_FIRE_DATE} to {POST_FIRE_DATE}</div>
                
                    <h3>Project Overview</h3>
                    <p>This dashboard displays burn severity analysis using Sentinel-2 satellite imagery. The dNBR (differenced Normalized Burn Ratio) method is used to classify burn severity into five categories.</p>
                    <p><strong>Total Study Area:</strong> {area_sqkm:.2f} km² ({area_ha:.2f} hectares)</p>
                </div>

                <div class="container">
                    <h3>📋 Data Sources & Methods</h3>
                    <p><strong>Satellite Data:</strong> Sentinel-2 Level-2A Surface Reflectance</p>
                    <p><strong>Analysis Method:</strong> dNBR (differenced Normalized Burn Ratio)</p>
                    <p><strong>Resolution:</strong> 30 meters</p>
                    <p><strong>Cloud Filter:</strong> &lt; 20% cloud coverage</p>
                    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                <div class="footer">
                    <p>Wildfire Burn Severity Analysis Dashboard | Generated using Google Earth Engine and Python</p>
                    <p>Data: Copernicus Sentinel-2 | Method: dNBR Classification</p>
                </div>
            </div>
        </div>
        <div class="main-content">
            <div class="map">
                <iframe id="mapFrame" src="map_{REGION_NAME}.html"></iframe>
            </div>
        </div>
    </div>
    <script>
        // Load the map initially
        document.getElementById('mapFrame').src = 'map_{REGION_NAME}.html';
        
        // Function to handle layer switching
        function showLayer(layerType) {{
            alert('In a full implementation, this would control map layers\\n\\nSelected: ' + layerType + ' layer');
        }}
        
        // Auto-refresh iframe every 30 seconds to ensure it loads
        setTimeout(function() {{
            var iframe = document.getElementById('mapFrame');
            iframe.src = iframe.src;
        }}, 30000);
        
        console.log('Wildfire Dashboard loaded for {REGION_NAME}');
    </script>
</body>
</html>
'''

# Save the dashboard HTML
dashboard_filename = f"./outputs/wildfire_dashboard_{REGION_NAME}.html"
with open(dashboard_filename, 'w', encoding='utf-8') as f:
    f.write(dashboard_html)

print(f"Interactive dashboard saved: {dashboard_filename}")
