#ifndef ASSETBOX_H
#define ASSETBOX_H

#include <QFrame>
#include <QColor>
#include <QString>

class QLabel;

// Class for asset price boxes
class AssetBox : public QFrame
{
    Q_OBJECT
    
public:
    AssetBox(const QString& assetName, double price, const QColor& color, QWidget* parent = nullptr);
    void UpdatePrice(double price);
    void UpdateColor(const QColor& color);
QString GetAssetName() const;

protected:
    void mousePressEvent(QMouseEvent *event) override;
signals:
    void clicked();
    
private:
    QLabel* m_labelName;
    QLabel* m_labelPrice;
    QString m_assetName;
};

#endif // ASSETBOX_H
