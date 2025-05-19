# Documents & Collections UI Guide

This guide describes the user interface for managing documents and collections in the Syft Agent's vector database.

## Access

The Documents & Collections interface can be accessed by clicking the database icon in the sidebar of the main application.

## Main Features

### 1. Database Overview
- **Total Collections**: Shows the number of collections in the database
- **Total Documents**: Displays the total number of documents across all collections
- **Status**: Indicates if the database is healthy (✓) or not (✗)

### 2. Collections Grid
- Displays all collections as cards
- Each card shows:
  - Collection name
  - Number of documents
  - Description (if available)
- Click on a collection to view its details

### 3. Collection Details
When a collection is selected, you can:

#### Search Tab
- Enter a query to search for similar documents
- Results show document content with similarity scores
- Supports semantic search using vector embeddings

#### Documents Tab
- View all documents in the collection
- Each document shows:
  - Document ID
  - Content preview
  - Metadata (JSON format)
- Delete documents using the trash icon

#### Insights Tab
- View collection statistics and insights
- (Future feature: visualization of document clusters)

### 4. Actions

#### Create Collection
1. Click "New Collection" button
2. Enter collection name (3-63 characters)
3. Optionally add a description
4. Click "Create Collection"

#### Add Document
1. Select a collection
2. Click "Add Document" button
3. Enter:
   - Document ID (unique identifier)
   - Content (text to be embedded)
   - Metadata (optional JSON)
4. Click "Add Document"

#### Delete Collection
1. Select a collection
2. Click "Delete Collection" button
3. Confirm the deletion

#### Delete Document
1. Navigate to Documents tab
2. Click trash icon next to document
3. Confirm deletion

## UI Features

### Dark Mode Support
The interface automatically adapts to the application's theme setting.

### Search Functionality
- Semantic search using vector embeddings
- Queries are automatically embedded and compared with stored documents
- Results are ranked by similarity

### Responsive Design
- Grid layout adapts to screen size
- Modal dialogs for forms
- Loading states for async operations

## Error Handling

- Error messages are displayed as alerts
- Network errors are handled gracefully
- Form validation prevents invalid data submission

## Performance Considerations

- Documents are loaded on demand
- Pagination for large collections (future enhancement)
- Efficient vector similarity search

## Future Enhancements

1. **Batch Operations**
   - Upload multiple documents at once
   - Bulk delete functionality

2. **Advanced Search**
   - Metadata filtering
   - Full-text search combination
   - Custom embedding functions

3. **Visualization**
   - Document clustering visualization
   - Embedding space exploration
   - Collection statistics charts

4. **Export/Import**
   - Export collections to JSON
   - Import documents from files
   - Backup and restore functionality