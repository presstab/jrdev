package chart

import (
	"fmt"
)

// PriceChart represents a chart for cryptocurrency prices
type PriceChart struct {
	AssetBoxes     map[string]*AssetBox
	ContextMenu    *ContextMenu
	TimeRangeDialog *TimeRangeDialog
	CryptoDb       *CryptoDatabase
}

// NewPriceChart creates a new price chart instance
func NewPriceChart() *PriceChart {
	return &PriceChart{
		AssetBoxes:     make(map[string]*AssetBox),
		ContextMenu:    nil,
		TimeRangeDialog: nil,
		CryptoDb:       nil,
	}
}

// Cleanup releases resources used by the price chart
func (p *PriceChart) Cleanup() {
	// Clean up asset boxes
	for coinName, assetBox := range p.AssetBoxes {
		assetBox.Dispose()
		delete(p.AssetBoxes, coinName)
	}
	
	// Clean up context menu
	if p.ContextMenu != nil {
		p.ContextMenu.Dispose()
		p.ContextMenu = nil
	}
	
	// Clean up time range dialog
	if p.TimeRangeDialog != nil {
		p.TimeRangeDialog.Dispose()
		p.TimeRangeDialog = nil
	}
	
	// Note: CryptoDb is owned by MainWindow, don't delete it here
}


// Check performs validation of the chart
func (p *PriceChart) Check() {
	// TODO: Add implementation details here later
	fmt.Println("Checking price chart...")
}