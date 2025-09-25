# Test Data Files for Choropleth Mapping

## 12 Different CSV Files for Testing

### ZIP Code Level Data (5 files)
1. **florida_zips_poverty.csv** - Florida poverty/ALICE household data (10 ZIPs)
2. **california_zips_income.csv** - California income data (10 ZIPs) 
3. **illinois_zips_crime.csv** - Illinois crime statistics (10 ZIPs)
4. **multi_state_zips_retail.csv** - Retail sales across Western states (10 ZIPs)
5. **northeast_zips_demographics.csv** - Population demographics (10 ZIPs)

### County Level Data (5 files)
6. **texas_counties_population.csv** - Texas population statistics (10 counties)
7. **newyork_counties_health.csv** - New York health metrics (10 counties)
8. **colorado_counties_housing.csv** - Colorado housing market data (10 counties)
9. **georgia_counties_voting.csv** - Georgia voter statistics (10 counties)

### State Level Data (3 files)
10. **us_states_education.csv** - Education statistics (10 states)
11. **us_states_economy.csv** - Economic indicators (10 states)
12. **midwest_states_agriculture.csv** - Agricultural production (10 states)

## Data Types Included
- **Demographic**: Population, age distribution, diversity
- **Economic**: Income, GDP, unemployment, poverty rates
- **Health**: Disease rates, life expectancy, mental health
- **Housing**: Home values, rent, ownership rates
- **Education**: Graduation rates, spending per student
- **Crime**: Violent and property crime rates
- **Agriculture**: Farm statistics, crop production
- **Voting**: Voter turnout, registration rates
- **Retail**: Sales data, e-commerce rates

## Geographic Coverage
- **States**: FL, CA, TX, NY, IL, CO, GA, AZ, WA, OR, MA, CT, PA, NJ, and more
- **Various Regions**: Northeast, Midwest, South, West
- **Mix of Urban/Rural**: Major cities and smaller areas

## Column Naming Conventions
- **ZIP identifiers**: ZIP, ZIP_Code, ZCTA, GEOID
- **County identifiers**: County, County_Name, County_FIPS, FIPS, FIPS_Code
- **State identifiers**: State, State_Name, State_Abbr, State_FIPS, State_Code

## Testing Scenarios
1. **Different geographic levels**: Test ZIP, County, and State joins
2. **Various data ranges**: Small values (percentages) to large (population in millions)
3. **Missing data**: Some files have different column structures
4. **Different naming conventions**: Test the tool's ability to identify geographic columns