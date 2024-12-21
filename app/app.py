from flask import Flask, render_template, request, jsonify
import pandas as pd
from unidecode import unidecode
import re

app = Flask(__name__)

# Load the dataset
df = pd.read_csv('SA_Aqar.csv')
df.dropna(inplace=True)

def normalize_search(text):
    """Normalize text for searching by removing accents and special characters"""
    if not isinstance(text, str):
        return str(text).lower()
    return unidecode(text).lower()

# Prepare search data
def prepare_search_data():
    locations = {
        'cities': sorted(df['city'].unique().tolist()),
        'districts': sorted(df['district'].unique().tolist())
    }
    
    # Create normalized versions for search
    locations['cities_normalized'] = {normalize_search(city): city for city in locations['cities']}
    locations['districts_normalized'] = {normalize_search(district): district for district in locations['districts']}
    
    return locations

@app.route('/')
def home():
    locations = prepare_search_data()
    
    # Get min and max values for numeric fields
    numeric_ranges = {
        'price': {'min': int(df['price'].min()), 'max': int(df['price'].max())},
        'size': {'min': int(df['size'].min()), 'max': int(df['size'].max())},
        'bedrooms': {'min': int(df['bedrooms'].min()), 'max': int(df['bedrooms'].max())},
        'bathrooms': {'min': int(df['bathrooms'].min()), 'max': int(df['bathrooms'].max())},
        'livingrooms': {'min': int(df['livingrooms'].min()), 'max': int(df['livingrooms'].max())}
    }
    
    return render_template('index.html', 
                         locations=locations,
                         numeric_ranges=numeric_ranges,
                         fronts=sorted(df['front'].unique().tolist()))

@app.route('/search-location', methods=['POST'])
def search_location():
    query = normalize_search(request.json.get('query', ''))
    location_type = request.json.get('type')  # 'city' or 'district'
    
    locations = prepare_search_data()
    normalized_dict = (locations['cities_normalized'] if location_type == 'city' 
                      else locations['districts_normalized'])
    
    # Filter locations based on query
    matches = [
        {'value': original, 'label': original}
        for normalized, original in normalized_dict.items()
        if query in normalized
    ]
    
    return jsonify(matches[:10])  # Limit to top 10 matches

@app.route('/filter', methods=['POST'])
def filter_data():
    filters = request.json
    filtered_df = df.copy()

    # Apply location filters
    if filters.get('city'):
        filtered_df = filtered_df[filtered_df['city'].isin(filters['city'])]
    if filters.get('district'):
        filtered_df = filtered_df[filtered_df['district'].isin(filters['district'])]
    if filters.get('front'):
        filtered_df = filtered_df[filtered_df['front'].isin(filters['front'])]

    # Apply price range filter
    if filters.get('price'):
        price_min = filters['price'].get('min')
        price_max = filters['price'].get('max')
        if price_min is not None and price_min != '':
            filtered_df = filtered_df[filtered_df['price'] >= float(price_min)]
        if price_max is not None and price_max != '':
            filtered_df = filtered_df[filtered_df['price'] <= float(price_max)]
            
    # Apply numeric filters with possible min and max
    
    for field in ['size', 'bedrooms', 'bathrooms', 'livingrooms']:
        if filters.get(field) is not None:
            if isinstance(filters[field], dict):
                # Handle min and max
                if 'min' in filters[field] and filters[field]['min'] is not None and filters[field]['min'] != '':
                    try:
                        min_val = int(filters[field]['min'])
                        filtered_df = filtered_df[filtered_df[field] >= min_val]
                    except ValueError:
                        # Handle invalid min value
                        pass
                if 'max' in filters[field] and filters[field]['max'] is not None and filters[field]['max'] != '':
                    try:
                        max_val = int(filters[field]['max'])
                        filtered_df = filtered_df[filtered_df[field] <= max_val]
                    except ValueError:
                        # Handle invalid max value
                        pass
            else:
                # Handle single value
                if filters[field] is not None and filters[field] != '':
                    try:
                        value = int(filters[field])
                        filtered_df = filtered_df[filtered_df[field] >= value]
                    except ValueError:
                        # Handle invalid value
                        pass
        
    # # Apply boolean filters
    for col in ['furnished', 'ac', 'roof', 'pool', 'frontyard', 'basement', 
                'duplex', 'stairs', 'elevator', 'fireplace']:
        if filters.get(col) is not None:
            filtered_df = filtered_df[filtered_df[col] == True] if filters[col] else filtered_df[filtered_df[col] == False]
    
    # Sort results by price
    filtered_df = filtered_df.sort_values('price')
    filtered_df = filtered_df[:5]
    return jsonify({
        'data': filtered_df.to_dict('records'),
        'count': int(len(filtered_df))
    })
if __name__ == '__main__':
    app.run(debug=True)