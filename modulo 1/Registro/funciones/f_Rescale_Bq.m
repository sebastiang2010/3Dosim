function [I,Actividad,UnitsPET]=f_Rescale_Bq(I,info,Rescale)


%% transformo en Bq/mL 
I=double(I);
a=info.RescaleType; 
if strcmp(a,'BQML')
    
    m=Rescale(:,1); 
    b=Rescale(:,2); 
    for i=1:size(I,3)
        I(:,:,i)=I(:,:,i).*m(i)+b(i); % Bq/ml
    end
end 

%% paso de Bq/ML a Bq    
vPET=[info.PixelSpacing;info.SliceThickness]; %mm
vPET=vPET./10; %cm

I=I.*prod(vPET); %Bq

%% Actividad 
Actividad=sum(I(:));

UnitsPET='Bq';
end
