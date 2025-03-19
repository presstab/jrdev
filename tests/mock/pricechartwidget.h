#ifndef PRICECHARTWIDGET_H
#define PRICECHARTWIDGET_H

#include <QWidget>
#include <QMap>
#include <QString>

class QMenu;
class QDialog;
class AssetBox;
class CryptoDatabase;

class PriceChartWidget : public QWidget
{
    Q_OBJECT
    
public:
    explicit PriceChartWidget(QWidget *parent = nullptr);
    ~PriceChartWidget();
    
    void SetDatabase(CryptoDatabase* db);
    void UpdateAssets();
    void Clear();
    
    // Function declaration with parameters
    void SetTimeRange(int days, bool refresh = true);
    
    // Declaration with const and override specifiers
    void Check() const override;
    
protected:
    void paintEvent(QPaintEvent *event) override;
    void resizeEvent(QResizeEvent *event) override;
    void contextMenuEvent(QContextMenuEvent *event) override;
    
private slots:
    void onAssetClicked();
    void onTimeRangeSelected();
    
private:
    CryptoDatabase* m_cryptodb;
    QMap<QString, AssetBox*> m_mapAssetBoxes;
    QMenu* m_contextMenu;
    QDialog* m_timeRangeDialog;
    int m_timeRangeDays;
};

#endif // PRICECHARTWIDGET_H