from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import Producto, Venta, DetalleVenta
from decimal import Decimal
@login_required
def cobro(request):
     # Obtener o crear carrito en la sesión
     carrito = request.session.get('carrito', [])
     
     if request.method == 'POST':
         if 'agregar_producto' in request.POST:
             # Agregar producto por código o búsqueda
             codigo = request.POST.get('codigo_barras', '').strip()
             nombre_busqueda = request.POST.get('nombre_producto', '').strip()
             
             producto = None
             if codigo:
                 producto = Producto.objects.filter(codigo_barras=codigo).first()
             elif nombre_busqueda:
                 producto = Producto.objects.filter(nombre__icontains=nombre_busqueda).first()
             
             if producto:
                 # Agregar al carrito
                 carrito.append({
                     'id': producto.id,
                     'nombre': producto.nombre,
                     'precio': float(producto.precio),
                     'cantidad': 1
                 })
                 request.session['carrito'] = carrito
         
         elif 'quitar_item' in request.POST:
             indice = int(request.POST.get('indice', 0))
             if 0 <= indice < len(carrito):
                 carrito.pop(indice)
                 request.session['carrito'] = carrito
         
         elif 'limpiar_carrito' in request.POST:
             request.session['carrito'] = []
             carrito = []
         
         elif 'cobrar' in request.POST:
             # Finalizar venta
             ##if not carrito:
               ##  return redirect('cobro')
             
             monto_recibido = Decimal(request.POST.get('monto_recibido', 0))
             total = sum(Decimal(item['precio']) * item['cantidad'] for item in carrito)
             
             if monto_recibido < total:
                 return render(request, 'ventas/pantalla_cobro.html', {
                     'carrito': carrito,
                     'total': total,
                     'error': 'El monto recibido es menor al total'
                 })
             
             vuelto = monto_recibido - total
             
             # Guardar venta en la base de datos
             venta = Venta.objects.create(
                 usuario=request.user,
                 total=total
             )
             
             for item in carrito:
                 producto = Producto.objects.get(id=item['id'])
                 DetalleVenta.objects.create(
                     venta=venta,
                     producto=producto,
                     cantidad=item['cantidad'],
                     subtotal=Decimal(item['precio']) * item['cantidad']
                 )
             
             # Limpiar carrito
             request.session['carrito'] = []
             
             return render(request, 'ventas/confirmacion.html', {
                 'venta': venta,
                 'total': total,
                 'monto_recibido': monto_recibido,
                 'vuelto': vuelto
             })
     
     total = sum(Decimal(item['precio']) * item['cantidad'] for item in carrito)
     
     return render(request, 'ventas/pantalla_cobro.html', {
         'carrito': carrito,
         'total': total
     })
@login_required
def lista_productos(request):
     productos = Producto.objects.all()
     return render(request, 'ventas/lista_productos.html', {'productos': productos})
@login_required
def agregar_producto(request):
     if request.method == 'POST':
         nombre = request.POST.get('nombre')
         precio = request.POST.get('precio')
         categoria_id = request.POST.get('categoria')
         stock = request.POST.get('stock', 0)
         codigo = request.POST.get('codigo_barras', '')
         
         from .models import Categoria
         categoria = get_object_or_404(Categoria, id=categoria_id)
         
         Producto.objects.create(
             nombre=nombre,
             precio=precio,
             categoria=categoria,
             stock=stock,
             codigo_barras=codigo
         )
         return redirect('lista_productos')
     
     from .models import Categoria
     categorias = Categoria.objects.all()
     return render(request, 'ventas/agregar_producto.html', {'categorias': categorias})
def inicio(request):
     return render(request, 'ventas/inicio.html')







