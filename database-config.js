/**
 * UNIFIED DATABASE CONFIGURATION
 * Connects all 5 repositories to the 3.1GB local database via API
 */

const DATABASE_CONFIG = {
    // Multiple data source options for reliability
    dataSources: [
        {
            name: 'local-api',
            url: 'http://localhost:5001',
            type: 'api',
            description: 'Local Tiger Census server (best quality - 3.1GB)',
            quality: 'excellent'
        },
        {
            name: 'github-regional',
            url: 'https://franzenjb.github.io/choropleth-mapper/data/regions',
            type: 'regional',
            description: 'GitHub regional chunks (good quality - <100MB each)',
            quality: 'good'
        },
        {
            name: 'github-basic',
            url: 'https://franzenjb.github.io/choropleth-mapper/data',
            type: 'static',
            description: 'GitHub basic files (demo quality - <50MB total)',
            quality: 'basic'
        },
        {
            name: 'github-demos',
            url: 'https://franzenjb.github.io/choropleth-mapper/data/demo_samples',
            type: 'demo',
            description: 'GitHub demo samples (specific use cases)',
            quality: 'demo'
        }
    ],
    
    // Current active source (will auto-switch)
    activeSource: null,
    
    // Geographic data endpoints
    endpoints: {
        counties: '/api/counties',
        states: '/api/states', 
        zips: '/api/zips',
        status: '/'
    },
    
    // Repository-specific configurations
    repositories: {
        'alice-choropleth-tool': {
            dataTypes: ['counties', 'zips', 'states'],
            priority: 'alice-data',
            localPath: '/Users/jefffranzen/alice-choropleth-tool/docs/boundaries/'
        },
        'choropleth-mapper': {
            dataTypes: ['counties', 'states', 'zips'],
            priority: 'comprehensive',
            localPath: '/Users/jefffranzen/choropleth-mapper/data/'
        },
        'universal-choropleth-tool': {
            dataTypes: ['counties', 'states', 'zips'],
            priority: 'universal',
            localPath: null // Uses API only
        },
        'bivariate-choropleth-tool': {
            dataTypes: ['counties', 'tracts', 'bg'],
            priority: 'statistical',
            localPath: null // Uses API only  
        },
        'alice-data-mapper': {
            dataTypes: ['counties', 'zips', 'tracts'],
            priority: 'processing',
            localPath: null // Uses API only
        }
    }
};

/**
 * Universal Database Service
 * Works with both local files and API server
 */
class UnifiedGISDatabase {
    constructor(repositoryName = 'unknown') {
        this.config = DATABASE_CONFIG;
        this.repository = repositoryName;
        this.cache = new Map();
        this.repoConfig = this.config.repositories[repositoryName] || {};
    }
    
    async findAvailableDataSource() {
        if (this.config.activeSource) {
            return this.config.activeSource;
        }
        
        for (const source of this.config.dataSources) {
            try {
                const testUrl = source.type === 'api' 
                    ? `${source.url}${this.config.endpoints.status}`
                    : `${source.url}/us_states.json`;
                    
                const response = await fetch(testUrl, { 
                    method: 'HEAD', 
                    timeout: 3000 
                });
                
                if (response.ok) {
                    console.log(`✅ Using data source: ${source.description}`);
                    this.config.activeSource = source;
                    return source;
                }
            } catch (error) {
                console.warn(`❌ Data source unavailable: ${source.description}`);
            }
        }
        
        throw new Error('No data sources available');
    }
    
    async getStatus() {
        try {
            const source = await this.findAvailableDataSource();
            const statusUrl = source.type === 'api' 
                ? `${source.url}${this.config.endpoints.status}`
                : `${source.url}/status.json`;
                
            const response = await fetch(statusUrl);
            const data = await response.json();
            return { ...data, activeSource: source.description };
        } catch (error) {
            return { 
                status: 'all-sources-unavailable', 
                error: error.message,
                availableSources: this.config.dataSources.map(s => s.description)
            };
        }
    }
    
    async getGeography(type) {
        const cacheKey = `geography_${type}`;
        if (this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey);
        }
        
        try {
            const source = await this.findAvailableDataSource();
            let data;
            
            if (source.type === 'api') {
                // Use API endpoints
                const endpoint = this.config.endpoints[type];
                const response = await fetch(`${source.url}${endpoint}`);
                if (!response.ok) throw new Error(`API error: ${response.status}`);
                data = await response.json();
            } else if (source.type === 'regional') {
                // Try to get regional data based on user's location/preference
                // For now, try northeast as example - this could be made smarter
                const regionalMappings = {
                    counties: '/northeast_full.json',
                    states: '/northeast_full.json',
                    zips: '/northeast_full.json'
                };
                
                const filepath = regionalMappings[type];
                if (!filepath) throw new Error(`No regional mapping for ${type}`);
                
                const response = await fetch(`${source.url}${filepath}`);
                if (!response.ok) throw new Error(`Regional file error: ${response.status}`);
                data = await response.json();
                
                // Filter to only the requested type if the file contains mixed data
                if (data.features && type === 'counties') {
                    data.features = data.features.filter(f => 
                        f.properties && (f.properties.COUNTY || f.properties.county)
                    );
                }
            } else if (source.type === 'demo') {
                // Use specific demo files
                const demoMappings = {
                    counties: '/florida_alice.json',
                    states: '/northeast_detailed.json'
                };
                
                const filepath = demoMappings[type];
                if (!filepath) throw new Error(`No demo mapping for ${type}`);
                
                const response = await fetch(`${source.url}${filepath}`);
                if (!response.ok) throw new Error(`Demo file error: ${response.status}`);
                data = await response.json();
            } else {
                // Use static file mappings (basic fallback)
                const staticMappings = {
                    counties: '/us_counties.json',
                    states: '/us_states.json', 
                    zips: '/us_zips_full_basic.json'  // Use the smaller version
                };
                
                const filepath = staticMappings[type];
                if (!filepath) throw new Error(`No static mapping for ${type}`);
                
                const response = await fetch(`${source.url}${filepath}`);
                if (!response.ok) throw new Error(`Static file error: ${response.status}`);
                data = await response.json();
            }
            
            this.cache.set(cacheKey, data);
            console.log(`📊 Loaded ${type} data from: ${source.description}`);
            return data;
            
        } catch (error) {
            console.error(`❌ Failed to load ${type}:`, error);
            // Try repository-specific local files as last resort
            if (this.repoConfig.localPath) {
                try {
                    return await this.loadLocalFile(type);
                } catch (localError) {
                    console.error(`❌ Local fallback also failed:`, localError);
                }
            }
            throw error;
        }
    }
    
    async loadLocalFile(type) {
        const localMappings = {
            counties: 'us_counties.json',
            states: 'us_states.json', 
            zips: 'us_zips_full.json'
        };
        
        const filename = localMappings[type];
        if (!filename || !this.repoConfig.localPath) {
            throw new Error(`No local file mapping for ${type}`);
        }
        
        const response = await fetch(`${this.repoConfig.localPath}${filename}`);
        if (!response.ok) {
            throw new Error(`Failed to load local file: ${filename}`);
        }
        
        return await response.json();
    }
}

// Export for use in repositories
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DATABASE_CONFIG, UnifiedGISDatabase };
}