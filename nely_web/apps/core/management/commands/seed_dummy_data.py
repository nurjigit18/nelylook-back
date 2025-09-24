# apps/core/management/commands/seed_dummy_data.py
from __future__ import annotations
import random, string
from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, IntegrityError, models
from django.apps import apps

try:
    from faker import Faker
except ImportError:
    Faker = None


# --------- utilities ----------
def by_table(table_name: str, startswith: bool = False) -> Optional[models.Model]:
    """
    Find a model class by its DB table name.
    If startswith=True, returns the first model whose db_table starts with table_name (useful for 'orders_orderitem*').
    """
    for m in apps.get_models():
        dbt = getattr(m._meta, "db_table", "")
        if (startswith and dbt.startswith(table_name)) or (not startswith and dbt == table_name):
            return m
    return None

def pick(seq):
    return random.choice(list(seq))

def rand_money(a=5, b=200):
    return Decimal(str(round(random.uniform(a, b), 2)))

def rand_rate(a=0.5, b=150):
    return Decimal(str(round(random.uniform(a, b), 6)))

def rand_code(prefix: str, n=6):
    import string as s
    return prefix + ''.join(random.choices(s.ascii_uppercase + s.digits, k=n))


class Command(BaseCommand):
    help = "Seed dummy data across your e-commerce tables (binds models by db_table names)."

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=10)
        parser.add_argument("--products", type=int, default=30)
        parser.add_argument("--orders", type=int, default=25)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--wipe", action="store_true")
        parser.add_argument("--no-images", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        if Faker is None:
            raise CommandError("Faker is not installed. Run: pip install Faker")

        random.seed(opts["seed"])
        fake = Faker(); Faker.seed(opts["seed"])

        # ---- bind by db_table (from your screenshot) ----
        User            = by_table("users")
        UserAddress     = by_table("user_addresses")

        Currency        = by_table("currencies")
        Color           = by_table("colors")
        Size            = by_table("sizes")
        Category        = by_table("categories")
        ClothingType    = by_table("clothing_types")

        Product         = by_table("products")
        ProductVariant  = by_table("product_variants")
        ProductImage    = by_table("product_images")
        ProductViews    = by_table("product_views")
        RelatedProducts = by_table("related_products")

        Collection      = by_table("collections")
        CollectionProd  = by_table("collection_products")

        ShoppingCart    = by_table("shopping_cart")
        CartItem        = by_table("cart_items")
        Wishlist        = by_table("wishlist_wishlists")  # likely a Wishlist model with db_table set like this

        Order           = by_table("orders_order")
        OrderItem       = by_table("orders_orderitem", startswith=True)  # handle orders_orderitems/orders_orderitem

        Payment         = by_table("payments")
        FxRate          = by_table("fx_rates")

        DeliveryZone    = by_table("delivery_zones")

        if opts["wipe"]:
            self.stdout.write(self.style.WARNING("Wiping existing dummy data (best effort)…"))
            self._wipe([
                Payment, OrderItem, Order, CartItem, ShoppingCart, Wishlist,
                CollectionProd, Collection, RelatedProducts, ProductViews, ProductImage,
                ProductVariant, Product, Category, ClothingType, Color, Size, Currency, FxRate
            ], user_model=User)

        users = self._seed_users(User, UserAddress, fake, count=opts["users"])
        currencies = self._seed_currencies(Currency)
        self._seed_fx_rates(FxRate, currencies)

        colors = self._seed_colors(Color)
        sizes = self._seed_sizes(Size)
        categories = self._seed_categories(Category)
        ctypes = self._seed_clothing_types(ClothingType)

        products, variants = self._seed_catalog(
            Product, ProductVariant, ProductImage, currencies, categories, ctypes, colors, sizes, fake,
            count=opts["products"], no_images=opts["no_images"]
        )

        self._seed_collections(Collection, CollectionProd, products)
        self._maybe_views_and_related(ProductViews, RelatedProducts, products)

        self._seed_carts(ShoppingCart, CartItem, users, variants)
        self._seed_wishlists(Wishlist, users, variants)

        self._seed_orders_and_payments(Order, OrderItem, Payment, users, variants, currencies, fake, count=opts["orders"])

        self.stdout.write(self.style.SUCCESS("✅ Dummy data seeded."))

    # ---------------- wipe ----------------
    def _wipe(self, models_list: List[Optional[models.Model]], user_model: Optional[models.Model]):
        for M in models_list:
            if not M: 
                continue
            try:
                M.objects.all().delete()
            except Exception:
                pass
        if user_model:
            try:
                # keep superusers if the model has such a field
                if hasattr(user_model, "is_superuser"):
                    user_model.objects.filter(is_superuser=False).delete()
                else:
                    user_model.objects.all().delete()
            except Exception:
                pass

    # ---------------- users ----------------
    def _seed_users(self, User, UserAddress, fake, count=10):
        if not User:
            return []
        users = []

        # admin
        admin = User.objects.filter(email="admin@example.com").first()
        if not admin:
            # guess field names
            fields = {f.name for f in User._meta.get_fields()}
            kwargs = {}
            if "email" in fields: kwargs["email"] = "admin@example.com"
            if "first_name" in fields: kwargs["first_name"] = "Admin"
            if "last_name"  in fields: kwargs["last_name"]  = "User"
            # create superuser if possible
            try:
                admin = User.objects.create_superuser(**kwargs, password="Admin123!")
            except Exception:
                admin = User.objects.create(**kwargs)
                if "is_staff" in fields: admin.is_staff = True
                if "is_superuser" in fields: admin.is_superuser = True
                admin.set_password("Admin123!"); admin.save()
        users.append(admin)

        u_fields = {f.name for f in User._meta.get_fields()}
        for i in range(count):
            email = f"user{i+1}@example.com" if "email" in u_fields else None
            q = {}
            if email: q["email"] = email
            u = User.objects.filter(**q).first() if q else None
            if not u:
                kwargs = {}
                if "email" in u_fields: kwargs["email"] = email
                if "first_name" in u_fields: kwargs["first_name"] = fake.first_name()
                if "last_name"  in u_fields: kwargs["last_name"]  = fake.last_name()
                if "phone" in u_fields: kwargs["phone"] = fake.msisdn()
                u = User.objects.create(**kwargs)
                try:
                    u.set_password("User123!"); u.save()
                except Exception:
                    pass
            users.append(u)

            if UserAddress:
                a_fields = {f.name for f in UserAddress._meta.get_fields()}
                try:
                    UserAddress.objects.get_or_create(
                        **({"user": u} if "user" in a_fields else {}),
                        defaults={
                            **({"line1": fake.street_address()} if "line1" in a_fields else {}),
                            **({"city": fake.city()} if "city" in a_fields else {}),
                            **({"postal_code": fake.postcode()} if "postal_code" in a_fields else {}),
                            **({"address_type": "shipping"} if "address_type" in a_fields else {}),
                        }
                    )
                except Exception:
                    pass
        return users

    # -------------- core data --------------
    def _seed_currencies(self, Currency):
        if not Currency: return []
        items = []
        data = [
            {"code": "KGS", "name": "Kyrgyz Som", "symbol": "c"},
            {"code": "USD", "name": "US Dollar", "symbol": "$"},
            {"code": "EUR", "name": "Euro", "symbol": "€"},
        ]
        fields = {f.name for f in Currency._meta.get_fields()}
        for row in data:
            key = {}
            if "code" in fields:
                key["code"] = row["code"]
            elif "iso" in fields:
                key["iso"] = row["code"]
            obj, _ = Currency.objects.get_or_create(**key, defaults={k: v for k, v in row.items() if k != "code"})
            items.append(obj)
        return items

    def _seed_fx_rates(self, FxRate, currencies):
        if not FxRate or not currencies: return
        now = datetime.utcnow()
        for base in currencies:
            for quote in currencies:
                if base == quote: continue
                try:
                    FxRate.objects.get_or_create(
                        base_currency=base, quote_currency=quote,
                        defaults={"rate": rand_rate(0.5, 150), "source": "dummy", "as_of": now}
                    )
                except Exception:
                    pass

    def _seed_colors(self, Color):
        if not Color: return []
        names = ["Black","White","Beige","Blue","Red","Green","Chocolate","Emerald","Pale Yellow","Gray"]
        items=[]
        f={f.name for f in Color._meta.get_fields()}
        for n in names:
            key = {"name": n} if "name" in f else {"code": n[:3].upper()}
            obj,_=Color.objects.get_or_create(**key)
            items.append(obj)
        return items

    def _seed_sizes(self, Size):
        if not Size: return []
        names = ["XS","S","M","L","XL","XXL"]
        items=[]
        f={f.name for f in Size._meta.get_fields()}
        for n in names:
            key = {"name": n} if "name" in f else {"code": n}
            obj,_=Size.objects.get_or_create(**key)
            items.append(obj)
        return items

    def _seed_categories(self, Category):
        if not Category: return []
        names = ["Dresses","Tracksuits","Tops","Jeans","Outerwear","Skirts","Accessories"]
        items=[]
        f={f.name for f in Category._meta.get_fields()}
        for n in names:
            key={}
            if "name" in f: key["name"]=n
            if "slug" in f: key["slug"]=n.lower().replace(" ","-")
            obj,_=Category.objects.get_or_create(**({ "name": n } if "name" in f else {"id": names.index(n)+1}),
                                                 defaults=key)
            items.append(obj)
        return items

    def _seed_clothing_types(self, ClothingType):
        if not ClothingType: return []
        names = ["Casual Dress","Evening Dress","T-Shirt","Hoodie","Pants","Coat","Skirt"]
        items=[]
        for n in names:
            obj,_=ClothingType.objects.get_or_create(name=n) if hasattr(ClothingType, "_meta") else (None, False)
            items.append(obj)
        return [i for i in items if i]

    # -------------- catalog --------------
    def _seed_catalog(self, Product, ProductVariant, ProductImage, currencies, categories, ctypes, colors, sizes, fake,
                      count=30, no_images=False):
        products, variants = [], []
        if not Product: return products, variants

        price_currency = currencies[0] if currencies else None
        p_fields = {f.name for f in Product._meta.get_fields()}
        v_fields = {f.name for f in ProductVariant._meta.get_fields()} if ProductVariant else set()
        for i in range(count):
            name = f"{pick(['Velvet','Classic','Minimal'])} {pick(['Dress','Tracksuit','Top','Coat'])} {i+1}"
            defaults = {}
            if "name" in p_fields: defaults["name"]=name
            if "slug" in p_fields: defaults["slug"]=name.lower().replace(" ","-")+f"-{i+1}"
            if "description" in p_fields: defaults["description"]=fake.paragraph(nb_sentences=3)
            if "base_price" in p_fields: defaults["base_price"]=rand_money(20,150)
            if "currency" in p_fields and price_currency: defaults["currency"]=price_currency
            if "category" in p_fields and categories: defaults["category"]=pick(categories)
            if "clothing_type" in p_fields and ctypes: defaults["clothing_type"]=pick(ctypes)
            if "status" in p_fields: defaults["status"]="active"

            key = {"name": defaults["name"]} if "name" in p_fields else {"id": i+1}
            product,_=Product.objects.get_or_create(**key, defaults=defaults)
            products.append(product)

            # image
            if ProductImage and not no_images:
                try:
                    pi_fields = {f.name for f in ProductImage._meta.get_fields()}
                    kwargs = {"product": product}
                    if "image_url" in pi_fields:
                        kwargs["image_url"] = f"https://picsum.photos/seed/{product.pk}/1200/1600"
                    ProductImage.objects.get_or_create(product=product, defaults=kwargs)
                except Exception:
                    pass

            # variants
            if ProductVariant:
                for _ in range(random.randint(3,6)):
                    vkw = {"product": product}
                    if "color" in v_fields and colors: vkw["color"]=pick(colors)
                    if "size"  in v_fields and sizes:  vkw["size"]=pick(sizes)
                    if "sku"   in v_fields:            vkw["sku"]=rand_code("SKU-")
                    if "price" in v_fields:
                        vkw["price"]=getattr(product,"base_price",rand_money(15,180))
                    if "currency" in v_fields and price_currency:
                        vkw["currency"]=price_currency
                    if "is_active" in v_fields: vkw["is_active"]=True

                    try:
                        key = {}
                        if "product" in v_fields and "color" in v_fields and "size" in v_fields:
                            key = {"product": product, "color": vkw.get("color"), "size": vkw.get("size")}
                        elif "sku" in v_fields:
                            key = {"sku": vkw.get("sku")}
                        variant,_=ProductVariant.objects.get_or_create(**key, defaults=vkw)
                        variants.append(variant)
                    except IntegrityError:
                        pass
        return products, variants

    # -------------- collections / related / views --------------
    def _seed_collections(self, Collection, CollectionProd, products):
        if not Collection or not CollectionProd or not products: return
        c1,_=Collection.objects.get_or_create(name="New Arrivals")
        c2,_=Collection.objects.get_or_create(name="Editor’s Picks")
        for p in random.sample(products, k=min(10, len(products))):
            CollectionProd.objects.get_or_create(collection=c1, product=p)
        for p in random.sample(products, k=min(10, len(products))):
            CollectionProd.objects.get_or_create(collection=c2, product=p)

    def _maybe_views_and_related(self, ProductViews, RelatedProducts, products):
        if ProductViews:
            for p in products:
                try:
                    ProductViews.objects.get_or_create(product=p, defaults={"views": random.randint(10, 500)})
                except Exception:
                    pass
        if RelatedProducts and len(products) >= 2:
            for p in products[: min(20, len(products))]:
                try:
                    rp = random.sample([x for x in products if x != p], k=min(2, len(products)-1))
                    for q in rp:
                        RelatedProducts.objects.get_or_create(product=p, related=q)
                except Exception:
                    pass

    # -------------- carts / wishlists --------------
    def _seed_carts(self, ShoppingCart, CartItem, users, variants):
        if not ShoppingCart or not CartItem or not users or not variants: return
        c_fields = {f.name for f in ShoppingCart._meta.get_fields()}
        i_fields = {f.name for f in CartItem._meta.get_fields()}
        for u in users:
            if getattr(u, "is_superuser", False): continue
            cart,_=ShoppingCart.objects.get_or_create(**({"user": u} if "user" in c_fields else {"session_id": f"u{u.pk}-session"}))
            for _ in range(random.randint(0,3)):
                v = pick(variants)
                kwargs = {"cart": cart}
                if "variant" in i_fields: kwargs["variant"]=v
                if "product" in i_fields and "product" not in kwargs: kwargs["product"]=getattr(v,"product",None)
                if "price" in i_fields: kwargs["price"]=getattr(v,"price",rand_money(10,100))
                if "quantity" in i_fields: kwargs["quantity"]=random.randint(1,3)
                CartItem.objects.get_or_create(**kwargs)

    def _seed_wishlists(self, Wishlist, users, variants):
        if not Wishlist or not users or not variants: return
        w_fields = {f.name for f in Wishlist._meta.get_fields()}
        # Some projects store FK to user directly and M2M to variants/products through a join table;
        # Here we just ensure there is at least one wishlist row per user for your UI.
        for u in users:
            if getattr(u, "is_superuser", False): continue
            try:
                if "user" in w_fields:
                    Wishlist.objects.get_or_create(user=u)
                else:
                    Wishlist.objects.get_or_create(name=f"{u.pk}-wishlist")
            except Exception:
                pass

    # -------------- orders / payments --------------
    def _seed_orders_and_payments(self, Order, OrderItem, Payment, users, variants, currencies, fake, count=25):
        if not Order or not OrderItem or not users or not variants: return
        o_fields = {f.name for f in Order._meta.get_fields()}
        i_fields = {f.name for f in OrderItem._meta.get_fields()}
        p_fields = {f.name for f in Payment._meta.get_fields()} if Payment else set()

        for _ in range(count):
            buyer = pick([u for u in users if not getattr(u, "is_superuser", False)])
            okw = {}
            if "user" in o_fields: okw["user"]=buyer
            if "status" in o_fields: okw["status"]=pick(["pending","paid","shipped","completed","canceled"])
            if "order_number" in o_fields: okw["order_number"]=rand_code("ORD-")
            if "currency" in o_fields and currencies: okw["currency"]=pick(currencies)
            if "total_amount" in o_fields: okw["total_amount"]=Decimal("0.00")
            order = Order.objects.create(**okw)

            total = Decimal("0.00")
            for v in random.sample(variants, k=min(random.randint(1,4), len(variants))):
                qty = random.randint(1,3)
                price = getattr(v,"price",rand_money(10,100))
                ikw = {"order": order, "quantity": qty}
                if "variant" in i_fields: ikw["variant"]=v
                if "product" in i_fields and "product" not in ikw: ikw["product"]=getattr(v,"product",None)
                if "unit_price" in i_fields: ikw["unit_price"]=price
                OrderItem.objects.create(**ikw)
                total += price * qty

            if "total_amount" in o_fields:
                setattr(order, "total_amount", total); order.save(update_fields=["total_amount"])

            if Payment:
                try:
                    pkw = {"order": order}
                    if "amount" in p_fields: pkw["amount"]=total
                    if "currency" in p_fields and "currency" in o_fields: pkw["currency"]=getattr(order,"currency",None)
                    if "status" in p_fields: pkw["status"]=pick(["pending","authorized","captured","failed","refunded"])
                    if "provider" in p_fields: pkw["provider"]=pick(["stripe","payme","manual"])
                    if "transaction_id" in p_fields: pkw["transaction_id"]=rand_code("PAY-")
                    if "paid_at" in p_fields: pkw["paid_at"]=datetime.utcnow()
                    Payment.objects.get_or_create(order=order, defaults=pkw)
                except Exception:
                    pass
