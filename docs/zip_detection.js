// ZIP Code prefix to state/region mapping
const ZIP_PREFIXES = {
    // Northeast
    '01': { state: 'MA', region: 'northeast' },
    '02': { state: 'MA', region: 'northeast' },
    '03': { state: 'NH', region: 'northeast' },
    '04': { state: 'ME', region: 'northeast' },
    '05': { state: 'VT', region: 'northeast' },
    '06': { state: 'CT', region: 'northeast' },
    '07': { state: 'NJ', region: 'northeast' },
    '08': { state: 'NJ', region: 'northeast' },
    '09': { state: 'AE', region: 'northeast' }, // Armed Forces Europe
    '10': { state: 'NY', region: 'northeast' },
    '11': { state: 'NY', region: 'northeast' },
    '12': { state: 'NY', region: 'northeast' },
    '13': { state: 'NY', region: 'northeast' },
    '14': { state: 'NY', region: 'northeast' },
    '15': { state: 'PA', region: 'northeast' },
    '16': { state: 'PA', region: 'northeast' },
    '17': { state: 'PA', region: 'northeast' },
    '18': { state: 'PA', region: 'northeast' },
    '19': { state: 'DE/PA', region: 'northeast' },
    
    // Southeast
    '20': { state: 'DC/VA', region: 'southeast' },
    '21': { state: 'MD', region: 'southeast' },
    '22': { state: 'VA', region: 'southeast' },
    '23': { state: 'VA', region: 'southeast' },
    '24': { state: 'WV', region: 'southeast' },
    '25': { state: 'WV', region: 'southeast' },
    '26': { state: 'WV', region: 'southeast' },
    '27': { state: 'NC', region: 'southeast' },
    '28': { state: 'NC', region: 'southeast' },
    '29': { state: 'SC', region: 'southeast' },
    '30': { state: 'GA', region: 'southeast' },
    '31': { state: 'GA', region: 'southeast' },
    '32': { state: 'FL', region: 'southeast' },
    '33': { state: 'FL', region: 'southeast' },
    '34': { state: 'FL', region: 'southeast' },
    '35': { state: 'AL', region: 'southeast' },
    '36': { state: 'AL', region: 'southeast' },
    '37': { state: 'TN', region: 'southeast' },
    '38': { state: 'TN', region: 'southeast' },
    '39': { state: 'MS', region: 'southeast' },
    '40': { state: 'KY', region: 'southeast' },
    '41': { state: 'KY', region: 'southeast' },
    '42': { state: 'KY', region: 'southeast' },
    
    // Midwest
    '43': { state: 'OH', region: 'midwest' },
    '44': { state: 'OH', region: 'midwest' },
    '45': { state: 'OH', region: 'midwest' },
    '46': { state: 'IN', region: 'midwest' },
    '47': { state: 'IN', region: 'midwest' },
    '48': { state: 'MI', region: 'midwest' },
    '49': { state: 'MI', region: 'midwest' },
    '50': { state: 'IA', region: 'midwest' },
    '51': { state: 'IA', region: 'midwest' },
    '52': { state: 'IA', region: 'midwest' },
    '53': { state: 'WI', region: 'midwest' },
    '54': { state: 'WI', region: 'midwest' },
    '55': { state: 'MN', region: 'midwest' },
    '56': { state: 'MN', region: 'midwest' },
    '57': { state: 'SD', region: 'midwest' },
    '58': { state: 'ND', region: 'midwest' },
    '60': { state: 'IL', region: 'midwest' },
    '61': { state: 'IL', region: 'midwest' },
    '62': { state: 'IL', region: 'midwest' },
    '63': { state: 'MO', region: 'midwest' },
    '64': { state: 'MO', region: 'midwest' },
    '65': { state: 'MO', region: 'midwest' },
    '66': { state: 'KS', region: 'midwest' },
    '67': { state: 'KS', region: 'midwest' },
    '68': { state: 'NE', region: 'midwest' },
    '69': { state: 'NE', region: 'midwest' },
    
    // South
    '70': { state: 'LA', region: 'south' },
    '71': { state: 'LA', region: 'south' },
    '72': { state: 'AR', region: 'south' },
    '73': { state: 'OK', region: 'south' },
    '74': { state: 'OK', region: 'south' },
    '75': { state: 'TX', region: 'south' },
    '76': { state: 'TX', region: 'south' },
    '77': { state: 'TX', region: 'south' },
    '78': { state: 'TX', region: 'south' },
    '79': { state: 'TX', region: 'south' },
    
    // West
    '80': { state: 'CO', region: 'west' },
    '81': { state: 'CO', region: 'west' },
    '82': { state: 'WY', region: 'west' },
    '83': { state: 'ID', region: 'west' },
    '84': { state: 'UT', region: 'west' },
    '85': { state: 'AZ', region: 'west' },
    '86': { state: 'AZ', region: 'west' },
    '87': { state: 'NM', region: 'west' },
    '88': { state: 'NM', region: 'west' },
    '89': { state: 'NV', region: 'west' },
    '90': { state: 'CA', region: 'west' },
    '91': { state: 'CA', region: 'west' },
    '92': { state: 'CA', region: 'west' },
    '93': { state: 'CA', region: 'west' },
    '94': { state: 'CA', region: 'west' },
    '95': { state: 'CA', region: 'west' },
    '96': { state: 'AP', region: 'west' }, // Armed Forces Pacific
    '97': { state: 'OR', region: 'west' },
    '98': { state: 'WA', region: 'west' },
    '99': { state: 'AK/WA', region: 'west' }
};

/**
 * Analyze ZIP codes in data to recommend the best geographic level
 * @param {Array} zipCodes - Array of ZIP code values from CSV
 * @returns {Object} Recommendation with level and confidence
 */
function analyzeZipCodes(zipCodes) {
    // Get unique prefixes (first 2 digits)
    const prefixes = new Set();
    const states = new Set();
    const regions = new Set();
    
    zipCodes.forEach(zip => {
        if (zip && /^\d{5}$/.test(String(zip))) {
            const prefix = String(zip).substring(0, 2);
            prefixes.add(prefix);
            
            const info = ZIP_PREFIXES[prefix];
            if (info) {
                states.add(info.state);
                regions.add(info.region);
            }
        }
    });
    
    // Determine recommendation based on distribution
    const recommendation = {
        prefixes: Array.from(prefixes),
        states: Array.from(states),
        regions: Array.from(regions),
        suggestedLevel: null,
        confidence: 'low',
        message: '',
        detail: ''
    };
    
    // Check for single state concentration
    if (states.size === 1) {
        const state = Array.from(states)[0];
        
        // Check if we have a specific state file available
        if (state === 'FL') {
            recommendation.suggestedLevel = 'zctas_fl';
            recommendation.confidence = 'very_high';
            recommendation.message = 'All ZIP codes are in Florida';
            recommendation.detail = '✅ Use Florida ZIP Codes for best performance';
        } else if (state === 'TX') {
            recommendation.suggestedLevel = 'zctas_tx';
            recommendation.confidence = 'very_high';
            recommendation.message = 'All ZIP codes are in Texas';
            recommendation.detail = '✅ Use Texas ZIP Codes for best performance';
        } else if (state === 'CA') {
            recommendation.suggestedLevel = 'zctas_ca';
            recommendation.confidence = 'very_high';
            recommendation.message = 'All ZIP codes are in California';
            recommendation.detail = '✅ Use California ZIP Codes for best performance';
        } else if (state === 'NY') {
            recommendation.suggestedLevel = 'zctas_ny';
            recommendation.confidence = 'very_high';
            recommendation.message = 'All ZIP codes are in New York';
            recommendation.detail = '✅ Use New York ZIP Codes for best performance';
        } else {
            // Use regional file
            const region = Array.from(regions)[0];
            recommendation.suggestedLevel = `zctas_${region}`;
            recommendation.confidence = 'high';
            recommendation.message = `ZIP codes are in ${state}`;
            recommendation.detail = `✅ Use ${region.charAt(0).toUpperCase() + region.slice(1)} ZIP Codes`;
        }
    }
    // Check for single region concentration
    else if (regions.size === 1) {
        const region = Array.from(regions)[0];
        recommendation.suggestedLevel = `zctas_${region}`;
        recommendation.confidence = 'high';
        recommendation.message = `ZIP codes span ${states.size} states in the ${region.charAt(0).toUpperCase() + region.slice(1)}`;
        recommendation.detail = `✅ Use ${region.charAt(0).toUpperCase() + region.slice(1)} ZIP Codes`;
    }
    // Multiple regions - need broader coverage
    else if (regions.size > 1) {
        // Determine which regions and suggest accordingly
        const regionList = Array.from(regions).map(r => r.charAt(0).toUpperCase() + r.slice(1)).join(', ');
        
        // Find the region with most ZIPs
        const regionCounts = {};
        prefixes.forEach(prefix => {
            const info = ZIP_PREFIXES[prefix];
            if (info) {
                regionCounts[info.region] = (regionCounts[info.region] || 0) + 1;
            }
        });
        
        const primaryRegion = Object.entries(regionCounts)
            .sort((a, b) => b[1] - a[1])[0][0];
        
        recommendation.suggestedLevel = `zctas_${primaryRegion}`;
        recommendation.confidence = 'medium';
        recommendation.message = `ZIP codes span multiple regions: ${regionList}`;
        recommendation.detail = `⚠️ Most ZIPs are in ${primaryRegion.charAt(0).toUpperCase() + primaryRegion.slice(1)} - you may need multiple regional files`;
    }
    
    return recommendation;
}