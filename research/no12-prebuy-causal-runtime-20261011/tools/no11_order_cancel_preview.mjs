/** Official three-argument cancel compiler at the existing synthetic boundary.
 * Only inert text with trigger=0; no Excel invocation, real id reservation,
 * broker cancellation, acknowledgement, funds release or portfolio mutation.
 */
import {digest} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
import {buildNo12SyntheticMsiiOrderText} from '../runtime/synthetic_msii_draft.mjs';
import {bindObservedOrder} from './no11_broker_order_state.mjs';
import {orderInstant,validMsiiOrderId,validateMsiiOrderIds,NS_PER_MS} from '../runtime/no11_order_boundary.mjs';
import {compileCancelArguments} from '../runtime/no11_msii_argument_contract.mjs';
const need=(ok,code)=>{if(!ok)throw Error('NO11_CANCEL_'+code)};
const validId=validMsiiOrderId;
const clock=x=>orderInstant(x,'NO11_CANCEL_SOURCE_CLOCK',{jstOnly:true});
export function buildSyntheticCancelText({orderRequest,sourceDraft,origin,source,cancelId,nowJst}){
 need(orderRequest&&source?.schemaId==='ARK_NO11_SYNTHETIC_CANCEL_SOURCE_V1'&&
  source.evidenceMode==='SYNTHETIC_OFFLINE_ONLY'&&source.productionReady===false&&source.orderTransmission===false,
  'SYNTHETIC_SOURCE_REQUIRED');
 const now=clock(nowJst),observed=clock(source.observedAtJst),created=clock(orderRequest.orderIdentity?.observedAt);
 need(observed.ns<=now.ns&&now.ns-observed.ns<=30000n*NS_PER_MS&&created.ns<=observed.ns,
  'SOURCE_CLOCK');
 need(source.sessionDate===nowJst.slice(0,10)&&source.observedAtJst.slice(0,10)===source.sessionDate&&
  orderRequest.orderIdentity.observedAt.slice(0,10)===source.sessionDate,'SOURCE_SESSION');
 need(validId(cancelId)&&validId(orderRequest.orderIdentity.reservedOrderId),'RSS_ID_RANGE');
 validateMsiiOrderIds(orderRequest.orderIdentity.usedOrderIds,'NO11_CANCEL_RSS_ID_RANGE');
 // Reconstruct at the original observation instant, not cancellation time.
 // This checks a synthetic stored preview; it never reserves an actual id.
 const original=buildNo12SyntheticMsiiOrderText({...orderRequest,now:orderRequest.orderIdentity.observedAt});
 need(sourceDraft&&digest(sourceDraft)===digest(original),'ORIGINAL_DRAFT_CHANGED');
 need(origin?.intentId===original.sourceIntentSha256&&origin.rssOrderId===original.rssOrderId&&
  origin.symbol===orderRequest.intent.symbol&&origin.side===orderRequest.intent.side&&
  origin.quantity===orderRequest.intent.quantity&&origin.account===source.account&&
  clock(origin.recordedAtJst).ns===created.ns,'ORIGIN_MISMATCH');
 const accountNames=['特定','一般','NISA（NISA成長投資枠）','旧NISA'];
 need(origin.account===accountNames[orderRequest.intent.accountType],'ACCOUNT_MISMATCH');
 need(Array.isArray(source.idRows)&&source.idRows.length<=5000&&Array.isArray(source.orders),'SOURCE_ROWS');
 const used=new Set();
 for(const row of source.idRows){need(validId(row.rssOrderId)&&!used.has(row.rssOrderId),'SOURCE_ID_DUPLICATE_OR_INVALID');used.add(row.rssOrderId);}
 need(cancelId!==original.rssOrderId&&!used.has(cancelId)&&!orderRequest.orderIdentity.usedOrderIds.includes(cancelId),'CANCEL_ID_ALREADY_USED');
 const link=bindObservedOrder({origin,idRows:source.idRows,orders:source.orders,sessionDate:source.sessionDate,throughJst:source.observedAtJst});
 need(['ACKNOWLEDGED','PARTIAL'].includes(link.order.phase)&&!link.order.terminal,'TARGET_NOT_CANCELLABLE');
 const number=link.brokerOrderNumber;
 need(/^[1-9]\d{0,14}$/.test(number)&&Number.isSafeInteger(Number(number)),'TARGET_NUMBER_INVALID');
 const args=compileCancelArguments({rssOrderId:cancelId,orderNumber:number});
 const core={schemaId:'ARK_NO11_MSII_CANCEL_TEXT_PREVIEW_V1',evidenceMode:'SYNTHETIC_OFFLINE_ONLY',
  function:'RssCancelOrder',arguments:args,formulaText:'=RssCancelOrder'+'('+args.join(',')+')',
  formulaCellType:'TEXT',trigger:0,sourceOrderDraftSha256:original.draftSha256,sourceSnapshotSha256:digest(source),
  targetOrderNumber:number,alreadyFilledQuantity:link.order.filledQty,remainingQuantity:link.order.quantity-link.order.filledQty,
  cancellationRequestedInBroker:false,cancellationAcknowledged:false,cashReserveReleased:false,
  formulaEvaluationAllowed:false,excelOrderWriteAllowed:false,brokerOrderIdActuallyReserved:false,
  productionReady:false,orderTransmission:false};
 return Object.freeze({...core,previewSha256:digest(core)});
}
