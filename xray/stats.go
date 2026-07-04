package xray

import (
	"errors"

	"github.com/xtls/xray-core/features/stats"
)

// QueryStats returns a snapshot of all traffic counters registered in the
// running Xray instance, keyed by counter name, e.g.
// "inbound>>>socks-in>>>traffic>>>uplink".
//
// The counters only exist when the running config enables "stats" and a
// "policy" that turns the traffic counters on; otherwise the returned map is
// empty (the core defaults to a no-op stats manager).
func QueryStats() (map[string]int64, error) {
	if coreServer == nil {
		return nil, errors.New("xray is not running")
	}

	manager, ok := coreServer.GetFeature(stats.ManagerType()).(stats.Manager)
	if !ok || manager == nil {
		return nil, errors.New("stats manager not available")
	}

	counters := make(map[string]int64)
	manager.VisitCounters(func(name string, c stats.Counter) bool {
		counters[name] = c.Value()
		return true
	})
	return counters, nil
}
