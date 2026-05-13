%%version 1.5 12/07/17

clc
%close all
%clear 
%numero de visulizaciones <10000
%disp(' ')
%-n=input(' Ingrese el numero de particulas (<1000): ');

%
fig=1; 

%%Hay que eliminar a mano las primeras columnas 
file=[];
[a,file]=f_cargo_ptract(file);




a2=zeros(100000,8);
n1=1;
for i=1:3:size(a,1)
    a1=a(i,:);
    a2(n1,:)=a1(1,1:8);
    a1=[];
    n1=n1+1;
end
 
% 
pos=a2(:,1:3);

vec=a2(:,4:6); 

E=a2(:,7);

wgt=a2(:,8);


figure(1)
 
hold on 
scatter3([pos(:,1);pos(:,1)],[pos(:,2);pos(:,2)],[pos(:,3);pos(:,3)]);
xlabel('X')
ylabel('Y')
zlabel('Z')



figure; % Crear una nueva figura
histogram(E, 'Normalization', 'probability', 'BinWidth', 0.05); % Normalizado por probabilidad

% Etiquetas y título
xlabel('Valores de E');
ylabel('Frecuencia');
title('Histograma del Vector E');

%% grafico el plano 
% % Coeficientes del plano

% A=-8.57044E-01;   
% B=1.49216E-02; 
% C=5.15027E-01; 
% D=-9.90259E+00;
% 
% % Crear una cuadrícula de puntos para x y y
% [x, y] = meshgrid(-10:0.1:10, -10:0.1:10); % Ajusta el rango según sea necesario
% 
% % Calcular z a partir de la ecuación del plano
% z = (D - A*x - B*y) / C;
% 
% %A1=-0.857044; 
% %B1=0.0149216; 
% %C1=0.515027; 
% D1=-10.80259;
% 
% z1= (D1 - A*x - B*y) / C;
% 
% % Graficar el plano
% figure(1);
% surf(x, y, z);
% %surf(x,y,z1); 
% % Mejorar la visualización
% xlabel(' Eje X');
% ylabel(' Eje Y');
% zlabel(' Eje Z');
% title(' Gráfico del Plano 3D');
% grid on;
% axis equal; % Mantiene las proporciones de los ejes

