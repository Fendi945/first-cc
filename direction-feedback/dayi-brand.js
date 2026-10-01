/**
 * DAYI Brand Component — locked to DAYI UI SYSTEM V1.6.
 * Single source of truth. Do not rebuild the logo inside individual pages.
 *
 * Standard:
 * - wordmark: dayi (never day1)
 * - Georgia / Times New Roman / serif
 * - warm black #222222
 * - i dot: brick red #C6402F
 * - desktop: 28px wordmark / 6px dot / top -5px
 * - mobile: 25px wordmark / ~5px dot
 * - Chinese lockup gap: 28px
 * - no separator dot / symbol between dayi and 大一造园
 */
(function(){
  if (customElements.get('dayi-brand')) return;

  class DayiBrand extends HTMLElement {
    connectedCallback() {
      if (this.shadowRoot) return;
      const root = this.attachShadow({mode:'open'});
      const chinese = this.hasAttribute('cn');
      root.innerHTML = `
        <style>
          :host{
            display:inline-block;
            color:#222222;
            line-height:1;
            vertical-align:middle;
          }
          .lockup{
            display:inline-flex;
            align-items:center;
            gap:28px;
            white-space:nowrap;
            min-height:28px;
          }
          .word{
            display:inline-flex;
            align-items:baseline;
            font-family:Georgia,"Times New Roman",serif;
            font-size:28px;
            font-weight:400;
            line-height:1;
            letter-spacing:0;
            color:#222222;
          }
          .brand-i{
            position:relative;
            display:inline-block;
            font-family:inherit;
            font-size:inherit;
            font-weight:inherit;
            line-height:inherit;
          }
          .brand-i::after{
            content:"";
            width:6px;
            height:6px;
            border-radius:50%;
            background:#C6402F;
            position:absolute;
            left:50%;
            transform:translateX(-50%);
            top:-5px;
          }
          .cn{
            font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei","Noto Sans SC",sans-serif;
            font-size:12px;
            font-weight:400;
            line-height:1;
            letter-spacing:.17em;
            color:#222222;
          }
          @media(max-width:720px){
            .lockup{min-height:25px}
            .word{font-size:25px}
            .brand-i::after{width:5px;height:5px;top:-4px}
            .cn{font-size:11px}
          }
        </style>
        <span class="lockup">
          <span class="word" role="img" aria-label="dayi"><span aria-hidden="true">day</span><span class="brand-i" aria-hidden="true">ı</span></span>
          ${chinese ? '<span class="cn">大一造园</span>' : ''}
        </span>
      `;
    }
  }

  customElements.define('dayi-brand', DayiBrand);
})();