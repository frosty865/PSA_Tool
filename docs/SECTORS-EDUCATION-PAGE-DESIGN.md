# Sectors & Subsectors Education Page - Design Recommendation

## Purpose
Create an educational page accessible to all users that visually displays the DHS Critical Infrastructure Sectors and their subsectors to help field personnel understand the taxonomy system.

## Recommended Approach

### 1. **Page Location**
- **Route**: `/sectors` or `/taxonomy`
- **Access**: All authenticated users (no admin required)
- **Navigation**: Add link in main navigation menu

### 2. **Visual Design**

#### Layout Options:

**Option A: Accordion/Collapsible Cards (Recommended)**
- Each sector as an expandable card
- Subsectors nested inside when expanded
- Clean, organized, easy to scan
- Mobile-friendly

**Option B: Tree/Diagram View**
- Visual hierarchy with lines/connectors
- More visual but potentially cluttered with 16 sectors
- Good for understanding relationships

**Option C: Grid/Table View**
- Sectors in cards, subsectors in expandable sections
- Good for quick reference
- Easy to search/filter

**Recommendation: Option A (Accordion) with search/filter**

### 3. **Features**

#### Core Features:
1. **Sector Cards**
   - Sector name (DHS official name)
   - Sector description (from database)
   - Count of subsectors
   - Expandable to show subsectors

2. **Subsector Display**
   - List of all subsectors for each sector
   - Subsector descriptions (if available)
   - Visual indentation to show hierarchy

3. **Search/Filter**
   - Search by sector or subsector name
   - Filter by sector
   - Real-time filtering

4. **Educational Context**
   - Header explaining these are DHS Critical Infrastructure Sectors
   - Brief explanation of how sectors/subsectors are used
   - Link to DHS CISA documentation (optional)

#### Additional Features:
- **Statistics**: Show total sectors (16 + General), total subsectors
- **Export**: Option to export as PDF or print-friendly view
- **Expand All/Collapse All**: Quick action buttons
- **Highlight**: Highlight "General" as a special case

### 4. **Data Structure**

Fetch from existing APIs:
- `/api/sectors` - Get all sectors with descriptions
- `/api/subsectors?sectorId=X` - Get subsectors for each sector

### 5. **User Experience**

#### Page Flow:
1. User lands on page
2. Sees all 16 DHS sectors + General in cards
3. Can expand any sector to see subsectors
4. Can search/filter to find specific sectors/subsectors
5. Can expand all to see full taxonomy

#### Visual Hierarchy:
```
[Sector Name] (16 subsectors) ▼
  ├─ Subsector 1
  ├─ Subsector 2
  └─ ...
```

### 6. **Implementation Details**

#### Components Needed:
- `SectorCard` - Individual sector with expand/collapse
- `SubsectorList` - List of subsectors for a sector
- `SectorSearch` - Search/filter component
- `SectorStats` - Statistics component

#### State Management:
- `sectors` - All sectors data
- `subsectors` - Map of sectorId -> subsectors
- `expandedSectors` - Set of expanded sector IDs
- `searchTerm` - Current search filter
- `selectedSector` - Filter by sector

### 7. **Styling**

Use existing CISA CSS variables:
- `--cisa-blue` for sector headers
- `--cisa-gray` for descriptions
- Card-based layout with shadows
- Responsive design for mobile

### 8. **Accessibility**

- Keyboard navigation (Tab to navigate, Enter to expand)
- ARIA labels for screen readers
- High contrast for readability
- Focus indicators

## Implementation Plan

1. Create `/app/sectors/page.jsx`
2. Add navigation link in `components/Navigation.jsx`
3. Create reusable components for sector cards
4. Implement search/filter functionality
5. Add loading states and error handling
6. Test with all user roles

## Benefits

- **Education**: Field personnel understand taxonomy
- **Reference**: Quick lookup of sectors/subsectors
- **Consistency**: Helps ensure correct classification
- **Transparency**: Shows what sectors/subsectors are available

