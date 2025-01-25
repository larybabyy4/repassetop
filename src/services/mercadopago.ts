import mercadopago from 'mercadopago';
import { PromotionPlan } from '../types';

mercadopago.configure({
  access_token: process.env.MERCADO_PAGO_ACCESS_TOKEN!
});

const promotionPlans: PromotionPlan[] = [
  {
    id: 'top_7',
    name: 'Destaque Superior 7 dias',
    price: 50,
    durationDays: 7,
    position: 'top'
  },
  {
    id: 'featured_30',
    name: 'Destaque Premium 30 dias',
    price: 150,
    durationDays: 30,
    position: 'featured'
  }
];

export async function createPayment(planId: string, userId: string) {
  const plan = promotionPlans.find(p => p.id === planId);
  if (!plan) throw new Error('Plano não encontrado');

  const preference = {
    items: [
      {
        title: plan.name,
        unit_price: plan.price,
        quantity: 1,
      }
    ],
    external_reference: `${userId}-${planId}`,
    back_urls: {
      success: `${process.env.BOT_WEBHOOK_URL}/payment/success`,
      failure: `${process.env.BOT_WEBHOOK_URL}/payment/failure`
    }
  };

  return await mercadopago.preferences.create(preference);
}