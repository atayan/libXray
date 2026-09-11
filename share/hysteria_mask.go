package share

import (
	"github.com/xtls/xray-core/infra/conf"
)

// buildHy2FinalMask builds Hysteria2 QUIC bandwidth / salamander mask (shared by URI and Clash).
//
// `ports` and `hopInterval` are accepted and ignored. They used to build a
// `conf.UdpHop` onto `QuicParamsConfig.UdpHop`; the core has since moved
// port hopping out of the QUIC params and into the finalMask system, as a
// UDP mask (`infra/conf/transport_finalmask.go`, `udpmaskLoader["udphop"]`)
// whose shape is different — `mode`, `remotePorts`, `remoteIPs` rather than
// a port list and an interval.
//
// Dropped rather than translated, and the parameters kept rather than
// removed: this is a vendored fork, upstream will adapt to the new core on
// its own schedule, and a smaller diff is a cheaper one to carry across
// that. Nothing in this project builds configs through `share` — the app
// parses links in `manual_link.rs` and assembles configs in
// `core/xray_config` — so no caller loses anything it was using.
func buildHy2FinalMask(up, down, ports string, hopInterval *int32, obfsType, obfsPassword string) (*conf.FinalMask, error) {
	var quicParams *conf.QuicParamsConfig
	if up != "" || down != "" {
		quicParams = &conf.QuicParamsConfig{}
		quicParams.Congestion = "brutal"
		if up != "" {
			quicParams.BrutalUp = conf.Bandwidth(up)
		}
		if down != "" {
			quicParams.BrutalDown = conf.Bandwidth(down)
		}
	}

	var udpMasks []conf.Mask
	if obfsType == "salamander" && obfsPassword != "" {
		obfs := conf.Mask{Type: "salamander"}
		salamander := &conf.Salamander{Password: obfsPassword}
		salamanderRawMessage, err := convertJsonToRawMessage(salamander)
		if err != nil {
			return nil, err
		}
		obfs.Settings = &salamanderRawMessage
		udpMasks = []conf.Mask{obfs}
	}

	if quicParams == nil && len(udpMasks) == 0 {
		return nil, nil
	}
	return &conf.FinalMask{QuicParams: quicParams, Udp: udpMasks}, nil
}
