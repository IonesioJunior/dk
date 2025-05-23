// Simplified world map SVG path data
const WORLD_MAP_DATA = {
    viewBox: "0 0 2000 1000",
    continents: [
        // North America
        {
            name: "North America",
            path: "M 380 250 Q 400 220 450 200 L 520 180 L 600 170 L 680 165 L 750 170 L 800 180 L 850 200 L 900 220 L 920 250 L 900 280 L 850 320 L 800 350 L 750 380 L 680 400 L 600 410 L 520 400 L 450 380 L 400 350 L 380 320 L 370 280 Z M 300 200 L 350 190 L 370 210 L 340 230 L 300 220 Z"
        },
        // South America
        {
            name: "South America",
            path: "M 600 480 L 620 450 L 640 460 L 660 480 L 680 520 L 690 580 L 680 640 L 660 700 L 640 750 L 620 780 L 600 800 L 580 780 L 560 750 L 540 700 L 520 640 L 510 580 L 520 520 L 540 480 L 560 460 L 580 450 Z"
        },
        // Europe
        {
            name: "Europe",
            path: "M 950 250 L 1000 240 L 1050 235 L 1100 240 L 1120 250 L 1110 270 L 1080 290 L 1050 300 L 1000 305 L 960 300 L 940 280 L 940 260 Z"
        },
        // Africa
        {
            name: "Africa",
            path: "M 950 350 L 1000 340 L 1050 345 L 1100 360 L 1140 400 L 1160 450 L 1170 520 L 1160 600 L 1140 680 L 1100 750 L 1050 800 L 1000 820 L 950 800 L 900 750 L 860 680 L 840 600 L 830 520 L 840 450 L 860 400 L 900 360 L 940 350 Z"
        },
        // Asia
        {
            name: "Asia",
            path: "M 1150 200 L 1250 180 L 1350 170 L 1450 165 L 1550 170 L 1650 180 L 1750 200 L 1800 230 L 1820 270 L 1800 320 L 1750 370 L 1650 400 L 1550 420 L 1450 425 L 1350 420 L 1250 400 L 1150 370 L 1100 320 L 1090 270 L 1100 230 Z"
        },
        // Australia
        {
            name: "Australia",
            path: "M 1500 650 L 1580 640 L 1650 645 L 1700 660 L 1720 690 L 1700 720 L 1650 740 L 1580 745 L 1500 740 L 1450 720 L 1440 690 L 1450 660 Z"
        }
    ]
};

// Convert latitude/longitude to x/y coordinates on the map
function latLonToMapXY(lat, lon) {
    // Simple equirectangular projection
    const mapWidth = 2000;
    const mapHeight = 1000;

    // Convert longitude (-180 to 180) to x (0 to mapWidth)
    const x = (lon + 180) * (mapWidth / 360);

    // Convert latitude (-90 to 90) to y (0 to mapHeight)
    // Note: y is inverted in SVG (0 is top)
    const y = (90 - lat) * (mapHeight / 180);

    return { x, y };
}
