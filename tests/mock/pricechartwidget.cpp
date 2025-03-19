PriceChartWidget::~PriceChartWidget()
{
    // Clean up asset boxes
    for (auto& [strCoin, assetBox] : m_mapAssetBoxes) {
        delete assetBox;
    }
    m_mapAssetBoxes.clear();
    
    // Clean up context menu
    if (m_contextMenu) {
        delete m_contextMenu; // This will also delete the actions
    }
    
    // Clean up time range dialog
    if (m_timeRangeDialog) {
        delete m_timeRangeDialog;
    }
    
    // Note: m_cryptodb is owned by MainWindow, don't delete it here
}
// Check() implementation
void PriceChartWidget::Check() {
    // TODO: Add implementation details here later
    qDebug() << "howdy folks it is me!";

}
