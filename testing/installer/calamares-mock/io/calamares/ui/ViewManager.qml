// Stand-in for Calamares' ViewManager (only what the X-OS panels use), for offscreen renders.
pragma Singleton
import QtQuick
ListModel {
    property int currentStepIndex: 0
    readonly property bool lastStep: currentStepIndex === count - 1
    property string backLabel: "&Back"
    property string nextLabel: currentStepIndex === 5 ? "&Install" : "&Next"
    property string quitLabel: lastStep ? "&Done" : "&Cancel"
    property string backIcon: ""
    property string nextIcon: ""
    property string quitIcon: ""
    property string quitTooltip: ""
    property bool backEnabled: currentStepIndex > 0 && !lastStep
    property bool nextEnabled: !lastStep
    property bool quitEnabled: true
    property bool quitVisible: true
    property bool backAndNextVisible: true
    function rowCount() { return count }
    function back() {} function next() {} function quit() {}
    ListElement { display: "Welcome" } ListElement { display: "Location" }
    ListElement { display: "Keyboard" } ListElement { display: "Partitions" }
    ListElement { display: "Users" } ListElement { display: "Summary" }
    ListElement { display: "Install" } ListElement { display: "Finish" }
}
